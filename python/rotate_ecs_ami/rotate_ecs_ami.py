#!/usr/bin/env python3
# tested against python3.7+ specifically

import argparse
import logging
import time
import boto3
from botocore.config import Config


logging.basicConfig(format="%(asctime)s - %(message)s", level=logging.INFO)


class Session:
    def __init__(self, region="ap-southeast-2", clients=None):
        self.region = region

        if not clients:
            config = Config(retries=dict(max_attempts=15))
            self.clients = {
                "ecs": boto3.client("ecs", region_name=self.region, config=config),
                "ec2": boto3.client("ec2", region_name=self.region, config=config),
                "autoscaling": boto3.client(
                    "autoscaling", region_name=self.region, config=config
                ),
            }
        else:
            self.clients = clients


def find_outdated_asg(session):
    """
    Given the cluster specified at runtime, will find any EC2 instances attached that do
    not have the AMI ID specified at runtime. It will then return the set of all
    autoscaling groups these instances belong to.

    :param session: An object containing boto3 sessions, cluster, and AMI information
    :return: a set of ASG names
    """
    logging.info("Finding old instances")

    instances = session.clients["ecs"].list_container_instances(
        cluster=session.cluster, filter=f"attribute:ecs.ami-id != {session.ami}"
    )
    instance_description = session.clients["ecs"].describe_container_instances(
        cluster=session.cluster, containerInstances=instances["containerInstanceArns"]
    )
    instance_ids = [
        item["ec2InstanceId"] for item in instance_description["containerInstances"]
    ]

    asg_description = session.clients["autoscaling"].describe_auto_scaling_instances(
        InstanceIds=instance_ids
    )

    # return set
    return {
        blob["AutoScalingGroupName"] for blob in asg_description["AutoScalingInstances"]
    }


def detach_outdated_instances(session):
    """
    Detaches outdated EC2 instances from their ASG. Runs under the assumption that the
    launch configuration has been updated to use the new AMI (cloudformation). This
    results in new instances spinning up to replace, but still leaves the old instances
    attached to the ECS cluster.

    :param session: An object containing boto3 sessions, cluster, AMI, and ASG
        information
    :return: a set of detached EC2 instance IDs that have been detached from their ASG
    """
    logging.info("Detaching old instances")
    detached_instances = []

    for asg_name in session.asgs:

        asg_info = session.clients["autoscaling"].describe_auto_scaling_groups(
            AutoScalingGroupNames=[asg_name], MaxRecords=100
        )
        instance_ids = [
            instance["InstanceId"]
            for instance in asg_info["AutoScalingGroups"][0]["Instances"]
        ]

        # detach_instances can only handle max 20 instances in a call
        def chunks(l, n):
            """Yield successive n-sized chunks from l."""
            for i in range(0, len(l), n):
                yield l[i : i + n]

        id_groups = list(chunks(instance_ids, 20))

        for group in id_groups:
            response = session.clients["autoscaling"].detach_instances(
                InstanceIds=group,
                AutoScalingGroupName=asg_name,
                ShouldDecrementDesiredCapacity=False,
            )
            # Getting instance id from description
            for item in response["Activities"]:
                if item["Description"].startswith("Detaching"):
                    detached_instances.append(item["Description"].split(" ")[-1])

    return set(detached_instances)


def can_drain_instances(session):
    """
    Returns true when the ASG has registered the minimum number of instances and they've
    also successfully joined the cluster specified at runtime

    :param session:  An object containing boto3 sessions, cluster, AMI, and ASG
        information
    :return: bool
    """
    for asg in session.asgs:
        asg_result = session.clients["autoscaling"].describe_auto_scaling_groups(
            AutoScalingGroupNames=[asg]
        )

        min_num = asg_result["AutoScalingGroups"][0]["MinSize"]

        if not len(asg_result["AutoScalingGroups"][0]["Instances"]) >= min_num:
            return False

        for instance in asg_result["AutoScalingGroups"][0]["Instances"]:
            if (
                not instance["LifecycleState"] == "InService"
                or not instance["HealthStatus"] == "Healthy"
            ):
                return False

        list_result = session.clients["ecs"].list_container_instances(
            cluster=session.cluster, filter=f"attribute:ecs.ami-id == {session.ami}"
        )

        if not len(list_result["containerInstanceArns"]) >= min_num:
            return False

    return True


def drain_instances(session):
    """
    Sets the container instance to the DRAINING state. Default behaviour will wait till
    new containers have been provisioned on another instance before removing.

    Note: Not sure what the max number of instances a single call can update. AWS docs
    don't specify

    :param session: An object containing boto3 sessions, cluster, and AMI information
    :return: Dict response of a drain instance call
    """
    logging.info("Draining instances")

    response = session.clients["ecs"].list_container_instances(
        cluster=session.cluster, filter=f"attribute:ecs.ami-id != {session.ami}"
    )

    return session.clients["ecs"].update_container_instances_state(
        cluster=session.cluster,
        containerInstances=response["containerInstanceArns"],
        status="DRAINING",
    )


def can_deregister(session):
    """
    Returns True when detached instances no longer have containers running on them,
    meaning they can successfully be removed from the cluster without dropping
    connections.

    :param session: An object containing boto3 sessions, cluster, and AMI information
    :return: bool
    """
    result = session.clients["ecs"].list_container_instances(
        cluster=session.cluster, filter=f"attribute:ecs.ami-id != {session.ami}"
    )

    container_ids = [arn.split("/")[-1] for arn in result["containerInstanceArns"]]

    for instance in container_ids:
        task_results = session.clients["ecs"].list_tasks(
            cluster=session.cluster, containerInstance=instance, desiredStatus="RUNNING"
        )
        if task_results["taskArns"]:
            return False

    return True


def deregister(session):
    """
    Will remove EC2 instances from the cluster

    :param session: An object containing boto3 sessions, cluster, and AMI information
    :return: None
    """
    logging.info("Deregistering instances")
    result = session.clients["ecs"].list_container_instances(
        cluster=session.cluster, filter=f"attribute:ecs.ami-id != {session.ami}"
    )
    for instance in result["containerInstanceArns"]:
        session.clients["ecs"].deregister_container_instance(
            cluster=session.cluster, containerInstance=instance, force=False
        )


def terminate(session):
    """
    Will terminate EC2 instances

    :param session: An object containing boto3 sessions, and EC2 instance information
    :return:
    """
    logging.info("Terminating instances")
    session.clients["ec2"].terminate_instances(InstanceIds=list(session.instances))


def main(ami, cluster, region="ap-southeast-2", clients=None, snooze=60):
    """
    Linking all functions together in a useful manner. First get the ASG info for any
    instances attached to the cluster that do not match the AMI ID. Then detach them and
    wait till they are replaced by fresh instances.
    After replacement, drain the containers, and deregister and terminate them once
    complete

    :param ami: The AMI ID to rotate to
    :param cluster: The cluster ARN to rotate instances in
    :param region: The AWS region name
    :param clients: A dict of boto3 clients (ecs, autoscaling, ec2)
    :param snooze: The sleep length in seconds between successive wait calls
    :return: None
    """
    session = Session(region=region, clients=clients)
    session.ami = ami
    session.cluster = cluster

    session.asgs = find_outdated_asg(session)
    session.instances = detach_outdated_instances(session)

    logging.info("Checking to see if instances are added to the ASG")
    total_sleep = 0
    while not can_drain_instances(session):
        if total_sleep >= 10:
            raise Exception  # TODO - make a better exception
        logging.info("ASG still provisioning instances. Sleeping for %s", snooze)
        time.sleep(snooze)
        total_sleep += 1
    logging.info("Took %s minutes to provision new instances", total_sleep)

    drain_instances(session)

    logging.info("Checking to see if instances can be removed from the cluster")
    total_sleep = 0
    while not can_deregister(session):
        if total_sleep >= 20:
            raise Exception  # TODO - make a better exception
        logging.info("Containers still running on instances. Sleeping for %s", snooze)
        time.sleep(snooze)
        total_sleep += 1
    logging.info("Took %s minutes to rotate containers", total_sleep)

    deregister(session)
    terminate(session)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Rotate old AMIs in a given ECS cluster"
    )
    parser.add_argument(
        "ami", help="The updated AMI ID that instances will be rotated to"
    )
    parser.add_argument("cluster", help="The cluster name to rotate in")
    parser.add_argument("--region", dest="region", default="ap-southeast-2")
    args = parser.parse_args()

    main(ami=args.ami, cluster=args.cluster, region=args.region)
