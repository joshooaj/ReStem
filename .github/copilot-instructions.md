# Mux Minus Project Architecture and Standards

## Overview

Mux Minus is an open-source web application and API on top of the demucs project
created by Facebook Research. Read more about demucs at https://github.com/facebookresearch/demucs.

In short, demucs accepts a music file in any common format and using an AI model
it will separate one or more elements of the song into two or more files. For
example, a two-stem output might produce one file with just the vocals from the
original file, and the second file would contain everything else. And a four-stem
output would produce files for vocals, bass, drums, and "other" containing the
remaining audio elements that could not be classified. There is also a six-stem
model capable of isolating the wave forms for guitar and piano in addition to the
other elements.

The Mux Minus application sits on top of demucs and includes a traditional
product landing page at the root of the website explaining what you can do and
demonstrating it with a sample song that has already been processed into both
two stems isolating vocals, and six stems.

Users must register with an email address, and new accounts are provided with
three free credits allowing them to process three music files. If they like the
tool, they can purchase additional credits in packs of 5, 25, or 100 at a price
of $1.00, $4.00, and $15.00 respectively.

## Architecture

### Frontend

The project will use Django for the front end, the REST api, user management, and
administration. The frontend should look clean and modern, it should be accessible,
and engaging. It should follow Django project development patterns as much as
possible.

### Backend

The backend service will be accessible only internally by the frontend service.
It will use FastAPI to present a simple REST API the frontend can use to interact
with the demucs CLI.

The backend should allow a configurable number of concurrent jobs so that users
cannot accidentally, or maliciously DDOS the service and we maintain fairness.

### Data Flow

Users will be allowed to upload one or more files at a time through the frontend
web interface or REST API. The frontend will save those files to a shared volume
and send the backend a job which includes the path to the uploaded file, the
desired AI model name, and if performing a two-stem job, the name of the stem
to isolate: vocals, bass, drums. When demucs has completed the job, the files
are moved to a folder on the same shared volume. Users will then be able to play
the individual stems from the web interface, download them, or download a zip
file containing all stems from that job.

### Deployment

This project will run in a docker-compose project behind a reverse proxy. The
project will have a container for the backend service, frontend service, and a
database container using postgres.

## Payment System

Payments will be made through Square using the `squareup` python module which
is found here: https://pypi.org/project/squareup/ and the official docs can be
found here: https://developer.squareup.com/docs/sdks/python

## User Management

This is not a social site so we do not need to worry much about user profiles or
sharing or anything of that nature. Users can register with an email address, or
they can use Single Sign-on with their GitHub, Facebook, or other popular social
media account. Once registered, users can change their email address or password
if they signed up directly without using SSO, or they can delete their account
and data completely.

## File Management

To minimize exposure to copyright issues, we do not want to hold on to the
original music files at all, and we only want to retain the output files long
enough for the user to download them. I think a reasonable strategy to avoid
deleting files before the user has downloaded them is to hold on to them for up
to 24 hours. Once the files have expired, the demucs job should still be shown
in their dashboard, but the download button and the music playback options will
be grayed out.

## Job Queuing

We want to use job queuing and API rate limiting to avoid two problems:

1. Overwhelming the backend service with highly intensive CPU/GPU tasks.
2. Consuming excessive disk space for queued jobs.

We should not allow the user to upload an unlimited number of files to be processed
either through the web interface or the REST API. If a user has 5 or more jobs
queued, new uploads must wait. This means the web interface should allow any number
of uploads, but it can only actually send files to us while there are fewer than
5 jobs in progress or in the job queue. As jobs complete, the frontend can start
uploading new jobs. REST API users should get an HTTP response to indicate they
need to wait and try again later.

## REST API

Users should be able to use the REST API to...

1. Authenticate with an API token they generate from their account profile
2. List all jobs
3. Get a job by ID
4. Download files associated with a job
5. List the available models
6. Create a new job and upload a file
7. Delete jobs