from scripts import rotate_ecs_ami as rot


def test_session_init():
    session = rot.Session()

    assert session.region == "ap-southeast-2"
    assert len(session.clients) == 3
