from flask import abort
from googleapiclient.discovery import build
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

# PROJECT_ID = os.environ['GCLOUD_PROJECT_ID']
storage_client = storage.Client()
bucket = storage_client.get_bucket(config['stageBucket'])


def github_auto_deployer(request):
    validate(request)

    repository = request.get_json()['repository']
    local_repository = download(repository)
    archive = create_archive(local_repository)
    upload(archive)


def validate(request):
    signature = hmac.new(config.githubSecretToken, request.data, hashlib.sha1).hexdigest()
    if not hmac.compare_digest(signature, request.headers['X-Hub-Signature'].split('=')[1]):
        abort(403)
        raise Exception("Unauthorized access")


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
    blob_name = os.path.join('function/src', os.path.basename(archive))
    blob = bucket.blob(blob_name)
    blob.upload_from_filename(archive)
    print(f"Uploaded {archive} to gs://{bucket.name}/{blob_name}")
    os.remove(archive)
    return archive


if __name__ == '__main__':
    test_payload = {
        'repository': {
            "name": "GCloudFunctionTest",
            "full_name": "mpanelo/GCloudFunctionTest",
            "clone_url": "https://github.com/mpanelo/GCloudFunctionTest.git",
        }
    }
    github_auto_deployer(test_payload)
