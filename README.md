# pipelines

To use this repo, project should contain a `pipeline.yml` file in the root directory.

The `pipeline.yml` file should be a list of tasks to be done by the pipeline. 

```yml
tasks:
  - type: docker-build
    on: commit
    image: foo-image

```

`type`: can be one of
- `docker-build`

# type-specific parameters

## `docker-build`

`registry`: optional, defaults to `gitlab`. can be one of
- `gitlab`
- `docker-hub`

`repository`: optional, defaults to `haondt`

`image`: name of image

`context`: options, location of build context, defaults to `.`

`file`: (optional) path to dockerfile, defaults to `Dockerfile`

**notes**
- if the commit has a (semver-compliant) tag associated with it, the image will have the following labels
  - `latest`
  - `x.y.z`
  - `x.y`

- otherwise, the image will have the following labels
  - `<commit-hash>`
