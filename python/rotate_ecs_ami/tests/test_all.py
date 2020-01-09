from scripts import rotate_ecs_ami as rot
from .boto_stubs import deregister_container_instance as dereg_con_inst_result
from .boto_stubs import describe_autoscaling_group as des_asg_grp_result
from .boto_stubs import describe_autoscaling_instances as desc_asg_inst_result
from .boto_stubs import describe_container_instances as desc_cont_result
from .boto_stubs import detach_instances as det_inst_result
from .boto_stubs import list_container_instances as list_cont_result
from .boto_stubs import list_tasks as list_task_result
from .boto_stubs import terminate_instances as terminate_result
from .boto_stubs import update_container_instances_state as update_cont_result
import copy
import pytest
import boto3
from botocore.stub import Stubber

AMI = "ami-11111111111111111"
ASGS = {"some-cluster-ECSAutoScalingGroup-ASDF1234"}
CLUSTER = "arn:aws:ecs:ap-southeast-2:111111111111:cluster/some-cluster"
CONTAINER_INSTANCE_IDS = [
    blob["ec2InstanceId"] for blob in desc_cont_result["containerInstances"]
]
EC2_INSTANCE_IDS = [
    item["InstanceId"]
    for item in des_asg_grp_result["AutoScalingGroups"][0]["Instances"]
]


@pytest.fixture
def boto3_clients():
    return {
        "ecs": boto3.client("ecs", region_name="ap-southeast-2"),
        "autoscaling": boto3.client("autoscaling", region_name="ap-southeast-2"),
        "ec2": boto3.client("ec2", region_name="ap-southeast-2"),
    }


def test_find_outdated_asg(boto3_clients):
    session = rot.Session(clients=boto3_clients)
    session.ami = AMI
    session.cluster = CLUSTER

    stubs = {k: Stubber(v) for k, v in session.clients.items()}

    stubs["ecs"].add_response(
        method="list_container_instances",
        service_response=list_cont_result,
        expected_params={
            "cluster": CLUSTER,
            "filter": f"attribute:ecs.ami-id != {AMI}",
        },
    )
    stubs["ecs"].add_response(
        method="describe_container_instances",
        service_response=desc_cont_result,
        expected_params={
            "cluster": CLUSTER,
            "containerInstances": list_cont_result["containerInstanceArns"],
        },
    )
    stubs["autoscaling"].add_response(
        method="describe_auto_scaling_instances",
        service_response=desc_asg_inst_result,
        expected_params={"InstanceIds": CONTAINER_INSTANCE_IDS},
    )

    for stub in stubs.values():
        stub.activate()

    assert rot.find_outdated_asg(session) == {
        "some-cluster-ECSAutoScalingGroup-ASDF1234"
    }

    for stub in stubs.values():
        stub.assert_no_pending_responses()
        stub.deactivate()


def test_detach_outdated_instances(boto3_clients):

    session = rot.Session(clients=boto3_clients)
    session.ami = AMI
    session.asgs = ASGS
    session.cluster = CLUSTER

    desired_result = {"i-111a1a1aaa1a1aa11", "i-11111b1b1bb1bbb1b"}

    with Stubber(boto3_clients["autoscaling"]) as stubber:
        stubber.add_response(
            method="describe_auto_scaling_groups",
            service_response=des_asg_grp_result,
            expected_params={"AutoScalingGroupNames": list(ASGS), "MaxRecords": 100},
        )
        stubber.add_response(
            method="detach_instances",
            service_response=det_inst_result,
            expected_params={
                "InstanceIds": EC2_INSTANCE_IDS,
                "AutoScalingGroupName": list(ASGS)[0],
                "ShouldDecrementDesiredCapacity": False,
            },
        )

        assert rot.detach_outdated_instances(session) == desired_result

        stubber.assert_no_pending_responses()


def test_drain_instances(boto3_clients):
    session = rot.Session(clients=boto3_clients)
    session.ami = AMI
    session.cluster = CLUSTER

    with Stubber(boto3_clients["ecs"]) as stubber:
        stubber.add_response(
            method="list_container_instances",
            service_response=list_cont_result,
            expected_params={
                "cluster": CLUSTER,
                "filter": f"attribute:ecs.ami-id != {AMI}",
            },
        )
        stubber.add_response(
            method="update_container_instances_state",
            service_response=update_cont_result,
            expected_params={
                "cluster": CLUSTER,
                "containerInstances": list_cont_result["containerInstanceArns"],
                "status": "DRAINING",
            },
        )

        rot.drain_instances(session)

        stubber.assert_no_pending_responses()


def test_can_update_service(boto3_clients):
    session = rot.Session(clients=boto3_clients)
    session.ami = AMI
    session.asgs = ASGS
    session.cluster = CLUSTER

    bad_result_a = copy.deepcopy(des_asg_grp_result)
    bad_result_a["AutoScalingGroups"][0]["Instances"][0]["LifecycleState"] = "Pending"
    del bad_result_a["AutoScalingGroups"][0]["Instances"][1]

    bad_result_b = copy.deepcopy(des_asg_grp_result)
    bad_result_b["AutoScalingGroups"][0]["Instances"][0]["LifecycleState"] = "Pending"

    bad_result_c = copy.deepcopy(list_cont_result)
    del bad_result_c["containerInstanceArns"][1]

    stubs = {k: Stubber(v) for k, v in boto3_clients.items()}

    stubs["autoscaling"].add_response(
        method="describe_auto_scaling_groups",
        service_response=bad_result_a,
        expected_params={"AutoScalingGroupNames": list(ASGS)},
    )
    stubs["autoscaling"].add_response(
        method="describe_auto_scaling_groups",
        service_response=bad_result_b,
        expected_params={"AutoScalingGroupNames": list(ASGS)},
    )
    stubs["autoscaling"].add_response(
        method="describe_auto_scaling_groups",
        service_response=des_asg_grp_result,
        expected_params={"AutoScalingGroupNames": list(ASGS)},
    )

    stubs["ecs"].add_response(
        method="list_container_instances",
        service_response=bad_result_c,
        expected_params={
            "cluster": CLUSTER,
            "filter": f"attribute:ecs.ami-id == {AMI}",
        },
    )

    stubs["autoscaling"].add_response(
        method="describe_auto_scaling_groups",
        service_response=des_asg_grp_result,
        expected_params={"AutoScalingGroupNames": list(ASGS)},
    )

    stubs["ecs"].add_response(
        method="list_container_instances",
        service_response=list_cont_result,
        expected_params={
            "cluster": CLUSTER,
            "filter": f"attribute:ecs.ami-id == {AMI}",
        },
    )
    for stub in stubs.values():
        stub.activate()

    assert rot.can_drain_instances(session) is False
    assert rot.can_drain_instances(session) is False
    assert rot.can_drain_instances(session) is False
    assert rot.can_drain_instances(session) is True

    for stub in stubs.values():
        stub.assert_no_pending_responses()
        stub.deactivate()


def test_can_deregister(boto3_clients):
    session = rot.Session(clients=boto3_clients)
    session.ami = AMI
    session.asgs = ASGS
    session.cluster = CLUSTER

    containers = copy.deepcopy(list_cont_result)
    containers["containerInstanceArns"] = [
        "arn:aws:ecs:ap-southeast-2:111111111111:container-instance/some-cluster/a99b9853b6114c87af46c7501a3a6ba8"
    ]
    success_result = copy.deepcopy(list_task_result)
    success_result["taskArns"] = []

    with Stubber(boto3_clients["ecs"]) as stubber:
        stubber.add_response(
            method="list_container_instances",
            service_response=containers,
            expected_params={
                "cluster": CLUSTER,
                "filter": f"attribute:ecs.ami-id != {AMI}",
            },
        )
        stubber.add_response(method="list_tasks", service_response=list_task_result)

        stubber.add_response(
            method="list_container_instances",
            service_response=containers,
            expected_params={
                "cluster": CLUSTER,
                "filter": f"attribute:ecs.ami-id != {AMI}",
            },
        )
        stubber.add_response(method="list_tasks", service_response=success_result)

        assert rot.can_deregister(session) is False
        assert rot.can_deregister(session) is True

        stubber.assert_no_pending_responses()


def test_deregister(boto3_clients):
    session = rot.Session(clients=boto3_clients)
    session.ami = AMI
    session.cluster = CLUSTER

    dereg_resp_a = copy.deepcopy(dereg_con_inst_result)
    dereg_resp_a["containerInstance"][
        "containerInstanceArn"
    ] = "arn:aws:ecs:ap-southeast-2:111111111111:container-instance/some-cluster/a99b9853b6114c87af46c7501a3a6ba8"
    dereg_resp_b = copy.deepcopy(dereg_con_inst_result)
    dereg_resp_b["containerInstance"][
        "containerInstanceArn"
    ] = "arn:aws:ecs:ap-southeast-2:111111111111:container-instance/some-cluster/e338a4bea54e4e06b664530a30ae02dd"

    with Stubber(boto3_clients["ecs"]) as stubber:
        stubber.add_response(
            method="list_container_instances",
            service_response=list_cont_result,
            expected_params={
                "cluster": CLUSTER,
                "filter": f"attribute:ecs.ami-id != {AMI}",
            },
        )
        stubber.add_response(
            method="deregister_container_instance", service_response=dereg_resp_a
        )
        stubber.add_response(
            method="deregister_container_instance", service_response=dereg_resp_b
        )

        rot.deregister(session)

        stubber.assert_no_pending_responses()


def test_terminate(boto3_clients):

    session = rot.Session(clients=boto3_clients)
    session.instances = ["i-11a111aa1111aa111", "i-222222222b2222222"]

    with Stubber(boto3_clients["ec2"]) as stubber:
        stubber.add_response(
            method="terminate_instances", service_response=terminate_result
        )
        rot.terminate(session)

        stubber.assert_no_pending_responses()


@pytest.mark.slow
def test_main(boto3_clients):
    stubs = {k: Stubber(v) for k, v in boto3_clients.items()}

    containers = copy.deepcopy(list_cont_result)
    containers["containerInstanceArns"] = [
        "arn:aws:ecs:ap-southeast-2:111111111111:container-instance/some-cluster/a99b9853b6114c87af46c7501a3a6ba8"
    ]

    success_result = copy.deepcopy(list_task_result)
    success_result["taskArns"] = []

    dereg_resp_a = copy.deepcopy(dereg_con_inst_result)
    dereg_resp_a["containerInstance"][
        "containerInstanceArn"
    ] = "arn:aws:ecs:ap-southeast-2:111111111111:container-instance/some-cluster/a99b9853b6114c87af46c7501a3a6ba8"

    dereg_resp_b = copy.deepcopy(dereg_con_inst_result)
    dereg_resp_b["containerInstance"][
        "containerInstanceArn"
    ] = "arn:aws:ecs:ap-southeast-2:111111111111:container-instance/some-cluster/e338a4bea54e4e06b664530a30ae02dd"

    bad_result_a = copy.deepcopy(des_asg_grp_result)
    bad_result_a["AutoScalingGroups"][0]["Instances"][0]["LifecycleState"] = "Pending"
    del bad_result_a["AutoScalingGroups"][0]["Instances"][1]

    # find_outdated_asg
    stubs["ecs"].add_response(
        method="list_container_instances", service_response=list_cont_result
    )
    # find_outdated_asg
    stubs["ecs"].add_response(
        method="describe_container_instances", service_response=desc_cont_result
    )

    # can_update_service
    stubs["ecs"].add_response(
        method="list_container_instances",
        service_response=list_cont_result,
        expected_params={
            "cluster": CLUSTER,
            "filter": f"attribute:ecs.ami-id == {AMI}",
        },
    )

    # drain_instances
    stubs["ecs"].add_response(
        method="list_container_instances",
        service_response=list_cont_result,
        expected_params={
            "cluster": CLUSTER,
            "filter": f"attribute:ecs.ami-id != {AMI}",
        },
    )
    # drain_instances
    stubs["ecs"].add_response(
        method="update_container_instances_state",
        service_response=update_cont_result,
        expected_params={
            "cluster": CLUSTER,
            "containerInstances": list_cont_result["containerInstanceArns"],
            "status": "DRAINING",
        },
    )

    stubs["ecs"].add_response(
        method="list_container_instances",
        service_response=containers,
        expected_params={
            "cluster": CLUSTER,
            "filter": f"attribute:ecs.ami-id != {AMI}",
        },
    )
    stubs["ecs"].add_response(method="list_tasks", service_response=list_task_result)

    stubs["ecs"].add_response(
        method="list_container_instances",
        service_response=containers,
        expected_params={
            "cluster": CLUSTER,
            "filter": f"attribute:ecs.ami-id != {AMI}",
        },
    )
    stubs["ecs"].add_response(method="list_tasks", service_response=success_result)
    stubs["ecs"].add_response(
        method="list_container_instances",
        service_response=list_cont_result,
        expected_params={
            "cluster": CLUSTER,
            "filter": f"attribute:ecs.ami-id != {AMI}",
        },
    )
    stubs["ecs"].add_response(
        method="deregister_container_instance", service_response=dereg_resp_a
    )
    stubs["ecs"].add_response(
        method="deregister_container_instance", service_response=dereg_resp_b
    )

    # find_outdated_asg
    stubs["autoscaling"].add_response(
        method="describe_auto_scaling_instances", service_response=desc_asg_inst_result
    )
    # detach_outdated_instances
    stubs["autoscaling"].add_response(
        method="describe_auto_scaling_groups",
        service_response=des_asg_grp_result,
        expected_params={"AutoScalingGroupNames": list(ASGS), "MaxRecords": 100},
    )
    # detach_outdated_instances
    stubs["autoscaling"].add_response(
        method="detach_instances",
        service_response=det_inst_result,
        expected_params={
            "InstanceIds": EC2_INSTANCE_IDS,
            "AutoScalingGroupName": list(ASGS)[0],
            "ShouldDecrementDesiredCapacity": False,
        },
    )
    # can_update_service
    stubs["autoscaling"].add_response(
        method="describe_auto_scaling_groups",
        service_response=bad_result_a,
        expected_params={"AutoScalingGroupNames": list(ASGS)},
    )
    # can_update_service
    stubs["autoscaling"].add_response(
        method="describe_auto_scaling_groups",
        service_response=des_asg_grp_result,
        expected_params={"AutoScalingGroupNames": list(ASGS)},
    )

    stubs["ec2"].add_response(
        method="terminate_instances", service_response=terminate_result
    )

    for stub in stubs.values():
        stub.activate()

    rot.main(ami=AMI, cluster=CLUSTER, clients=boto3_clients, snooze=1)

    for stub in stubs.values():
        stub.assert_no_pending_responses()
        stub.deactivate()
