from flask import abort
from googleapiclient import discovery
from googleapiclient import errors
from google.cloud import storage
import hmac
import hashlib
import git
import json
import os
import random
import shutil
import string

with open('config.json') as config_file:
    config = json.load(config_file)

storage_client = storage.Client()
bucket = storage_client.get_bucket(config['stageBucket'])


def github_auto_deployer(request):
    validate(request)
    repository = request.get_json()['repository']
    local_repository = download(repository)
    archive = create_archive(local_repository)
    source_archive_url = upload(archive)
    deploy_function('test', source_archive_url)


def validate(request):
    signature = hmac.new(config['githubSecretToken'].encode(), request.data, hashlib.sha1).hexdigest()
    _, request_signature = request.headers.get('X-Hub-Signature', 'sha1=').split('=')

    if not hmac.compare_digest(signature, request_signature):
        abort(403)


def download(repository):
    destination = f"/tmp/{repository['name']}"
    git.Repo.clone_from(repository['clone_url'], destination)
    print(f"Cloned repository {repository['full_name']} to {destination}")
    return destination


def create_archive(local_repository):
    archive_filename = ''.join(random.choices(string.ascii_uppercase + string.digits, k=13))
    archive = shutil.make_archive(f"/tmp/{archive_filename}", 'zip', local_repository)
    shutil.rmtree(local_repository)
    print(f"Archived local repository {local_repository} to {archive}")
    return archive


def upload(archive):
    blob_name = os.path.basename(archive)
    blob = bucket.blob(blob_name)
    blob.upload_from_filename(archive)
    os.remove(archive)
    source_archive_url = f"gs://{bucket.name}/{blob_name}"
    print(f"Uploaded {archive} to {source_archive_url}")
    return source_archive_url


def deploy_function(name, source_archive_url):
    location = f"projects/{config['projectId']}/locations/{config['location']}"
    request_body = {
        'sourceArchiveUrl': source_archive_url,
        'name': f"{location}/functions/{name}",
        'runtime': 'python37',
        'httpsTrigger': {},
    }
    operation = create_or_update_function(location, request_body)
    print(operation)


def create_or_update_function(location, body):
    client = CloudFunctionClient()
    try:
        return client.create(location, body)
    except errors.HttpError as error:
        if error.resp.status == 409 and error.resp.reason == 'Conflict':
            return client.patch(body)
        raise error


class CloudFunctionClient:

    def __init__(self):
        self.service = discovery.build('cloudfunctions', 'v1')

    def create(self, location, body):
        return self.service.projects() \
            .locations() \
            .functions() \
            .create(location=location, body=body) \
            .execute()

    def patch(self, body):
        return self.service.projects() \
            .locations() \
            .functions() \
            .patch(name=body['name'], body=body) \
            .execute()
