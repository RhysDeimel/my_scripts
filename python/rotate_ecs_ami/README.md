# Rotate ECS AMI
Whenever a client had to update an AMI for their ECS cluster, they began a manual process of updating the launch config for an ASG, detach the instances from the ASG, wait for the new instances to be provisioned and join the cluster, then set tell each container to terminate.

They did this process because they were using gRPC, and did not want to drop any connections. Terminating each container individually meant they had control over the termination signal sent, and allowed the container to gracefully shutdown and offload sessions. They had tried automating it before, but whatever method they were using sent a more aggressive termination signal, and the containers terminated too abruptly.

I gave it another go, and managed to automate the process without dropped connections. Unfortunately, the script and tests are stuck half way through refactoring to a class based approach to reduce duplicate boto calls as my attention was shifted during the process.

I have also removed the stubs, and modified the tests because they might contain company identifying data.
