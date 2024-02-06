# from datetime import timedelta
# from io import StringIO
from datetime import datetime, timezone
from time import time
from typing import Union
from uuid import uuid1

start_time = time()

import logging
from json import dumps, loads

# from mimetypes import guess_type
from pathlib import Path, PurePath
import functions_framework
from flask import abort, g, make_response
from flask_expects_json import expects_json
from os import environ
import os
import sys
from typing import Tuple, List

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))
from util_helpers import (
    impersonate_account,
    create_outgoing_file_ref,
    handle_bad_request,
    handle_exception,
    handle_not_found,
)
from util_input_validation import schema, Config
from metrics import calculate_metrics
from nlp import nlp_spacy
from spellcheck import spellcheck

### Azure Function Imports
import json
import azure.functions as func
from azure.storage.blob import BlobServiceClient, BlobSasPermissions, generate_blob_sas
from azure.core.exceptions import ResourceNotFoundError
from azure.identity import DefaultAzureCredential, ManagedIdentityCredential
from werkzeug.exceptions import InternalServerError, BadRequest, NotFound

### GLOBAL Vars

# Env Vars
# service = environ.get("K_SERVICE")
# environ["LD_LIBRARY_PATH"] = "/workspace/audiowaveform" + (
#     ":" + environ.get("LD_LIBRARY_PATH", "")
#     if environ.get("LD_LIBRARY_PATH") is not None
#     else ""
# ) 

# Instance-wide storage Vars
instance_id = str(uuid1())
run_counter = 0
# storage_client = storage.Client()
connection_string = os.environ['StorageAccountConnectionString']
storage_client = BlobServiceClient.from_connection_string(connection_string)

time_cold_start = time() - start_time


### MAIN
# @functions_framework.http
# @expects_json(schema)

app = func.FunctionApp()
@app.function_name(name="wf_analyse_HttpTrigger1")
@app.route(route="wf_analyse_HttpTrigger1")

def main(req: func.HttpRequest, context: func.Context) -> func.HttpResponse:
    """HTTP Cloud Function.
    Args:
        request (flask.Request): The request object.
        <https://flask.palletsprojects.com/en/1.1.x/api/#incoming-request-data>
    Returns:
        The response text, or any set of values that can be turned into a
        Response object using `make_response`
        <https://flask.palletsprojects.com/en/1.1.x/api/#flask.make_response>.
    """
    logging.basicConfig(level=logging.INFO)
    global run_counter
    run_counter += 1
    request_recieved = datetime.now(timezone.utc)
    request_json = req.get_json()
    CONFIG = Config(request_json)
    del request_json
    context = {
        **CONFIG.context.toJson(),
        "instance": instance_id,
        "instance_run": run_counter,
        "request_recieved": request_recieved.isoformat(),
    }

    # Output Variables
    response_json = {}
    out_files = {}

    transcript_blob = storage_client.get_container_client(
        CONFIG.input_files.transcript.bucket_name
    ).get_blob_client(
        CONFIG.input_files.transcript.full_path,
        # version_id=CONFIG.input_files.transcript.version,
    )

    try:
        # Try to fetch blob properties with the condition that the ETag must match the desired_etag
        etag_value = transcript_blob.get_blob_properties(if_match=CONFIG.input_files.transcript.version)
        logging.info(f'Transcript Blob Name: {transcript_blob.blob_name}')
        logging.info(f'Transcript Blob ETag: {etag_value["etag"]}')

    except ResourceNotFoundError:
        # Handle the case where the blob with the specified ETag is not found
        abort(404, "transcript file not found in bucket")

    # Download the blob as a string    
    transcript_content = transcript_blob.download_blob().readall()

    # Parse the JSON content
    transcript = json.loads(transcript_content)
    # logging.info(f"Transcipt json: {transcript}")

    #####################################################
    # Metrics
    #####################################################
    out_files["metrics"] = do_metrics(CONFIG, transcript)

    #####################################################
    # Spellcheck
    #####################################################

    if not ("metadata" in transcript and "media" in transcript["metadata"]
        and transcript["metadata"]["media"]["media_type"]=="voice"):
        ## Do spellcheck if spellcheck condition is met
        transcript, out_files["spellchecked_transcript"] = do_spellcheck(
            CONFIG, transcript
        )

    #####################################################
    # NLP
    #####################################################
    out_files["nlp"] = do_nlp(CONFIG, transcript)

    # Return with all the locations
    response_json["status"] = "success"
    response_json["staged_files"] = out_files
    # return make_response(response_json, 200)
    logging.info(f"response_json_output: {response_json}")
    return func.HttpResponse(body=dumps(response_json), status_code=200, mimetype='application/json')

def do_metrics(CONFIG: Config, transcript) -> dict:
    metrics = calculate_metrics(transcript)
    return upload_json("metrics", metrics, CONFIG)


def do_spellcheck(CONFIG: Config, transcript: dict) -> Tuple[dict, dict]:
    spellcheck_config = CONFIG.function_config.spellcheck_config
    spellchecked_transcript, spellcheck_time_taken = spellcheck(
        transcript, spellcheck_config
    )
    return (
        spellchecked_transcript,
        upload_json("spellchecked_transcript", spellchecked_transcript, CONFIG),
    )


def do_nlp(CONFIG: Config, spellchecked_transcript: dict) -> dict:
    nlp, nlp_time_taken = nlp_spacy(
        spellchecked_transcript, CONFIG.function_config.nlp_config
    )
    return upload_json("nlp", nlp, CONFIG)


def upload_json(type: str, data: dict, CONFIG: Config):
    staging_path = (
        Path(
            CONFIG.staging_config.folder_path,
            str(CONFIG.staging_config.file_prefix) + "_" + str(type),
        )
        .with_suffix(".json")
        .as_posix()
    )
    staging_blob = storage_client.get_container_client(CONFIG.staging_config.bucket_name).get_blob_client(
        staging_path
    )
    # staging_blob.upload_from_string(dumps(data), content_type="application/json")

    staging_blob.upload_blob(dumps(data),content_type='application/json', overwrite=True)
    
    if not staging_blob.exists():
        abort(500, "{} failed to upload to bucket".format(type))
    return create_outgoing_file_ref(staging_blob)
