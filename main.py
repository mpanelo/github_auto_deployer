from flask import abort
from flask import jsonify
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
import time

with open('config.json') as config_file:
    config = json.load(config_file)

AUTO_DEPLOYER = config['autoDeployer']
DEPLOYMENTS = config['deployments']

storage_client = storage.Client()
bucket = storage_client.get_bucket(AUTO_DEPLOYER['stagingBucket'])


def github_auto_deployer(request):
    validate(request)
    repository = request.get_json()['repository']
    local_repository = download(repository)
    archive = create_archive(local_repository)
    source_archive_url = upload(archive)
    function_config = get_function_config(repository, source_archive_url)
    result = deploy_function(function_config)
    return jsonify(result)


def validate(request):
    signature = hmac.new(AUTO_DEPLOYER['githubSecretToken'].encode(), request.data, hashlib.sha1).hexdigest()
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


def get_function_config(repository, source_archive_url):
    for deployment in DEPLOYMENTS:
        if deployment['repositoryName'] == repository['name']:
            function_config = deployment['cloudFunction']
            function_config['source'] = source_archive_url
            return function_config

    raise Exception(f"GitHub repository {repository['name']} does not have deployment configuration")


def deploy_function(function_config):
    location = f"projects/{AUTO_DEPLOYER['projectId']}/locations/{function_config['location']}"
    body = {
        'sourceArchiveUrl': function_config['source'],
        'name': f"{location}/functions/{function_config['name']}",
        'runtime': function_config['runtime'],
        'environmentVariables': function_config['environmentVariables'],
        'httpsTrigger': {},
    }
    client = CloudFunctionClient()
    operation = client.create_or_update(location, body)
    return client.poll(operation)


class CloudFunctionClient:

    def __init__(self):
        self.service = discovery.build('cloudfunctions', 'v1')

    def create_or_update(self, location, body):
        try:
            return self.create(location, body)
        except errors.HttpError as error:
            if error.resp.status == 409 and error.resp.reason == 'Conflict':
                return self.patch(body)
            raise error

    def create(self, location, body):
        print(f"Creating function {body['name']} in {location}")
        return self.service.projects() \
            .locations() \
            .functions() \
            .create(location=location, body=body) \
            .execute()

    def patch(self, body):
        print(f"Patching function {body['name']}")
        return self.service.projects() \
            .locations() \
            .functions() \
            .patch(name=body['name'], body=body) \
            .execute()

    def poll(self, operation):
        print('Waiting for operation to finish...')
        while True:
            response = self.service.operations() \
                .get(name=operation['name']) \
                .execute()

            if response.get('done', False):
                if 'error' in response:
                    raise Exception(response['error']['message'])
                print('Operation complete!')
                return response['response']

            time.sleep(1)
