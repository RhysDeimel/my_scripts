from clockwork import clockwork
import time
import random
import logging

logging.basicConfig(filename="status.log", level=logging.INFO)

api = clockwork.API("SECRET_KEY_HERE")

lyrics = open("bohemian.txt", "r").readlines()

for line in lyrics:
    payload = line.replace("\n", "")
    logging.info("Sending: {}".format(payload))
    message = clockwork.SMS(from_name="F Mercury", to="61000000000", message=payload)
    response = api.send(message)

    if response.success:
        logging.info("Success")
        logging.info(response.id)
        logging.info("\n")
    else:
        logging.info("Failure")
        logging.info(response.error_code)
        logging.info(response.error_message)
        logging.info("\n")
    time.sleep(random.randrange(300, 600))
    time.sleep(10)

logging.info("All done")
