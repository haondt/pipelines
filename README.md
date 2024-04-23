# pipelines

To use this repo, project should contain a `pipeline.yml` file in the root directory.

The `pipeline.yml` file should be a list of tasks to be done by the pipeline. 

```yml
tasks:
  - type: docker-build
    on: commit
    context: . # optional
    file: Dockefile # optional
    image: foo-image
    registries:
      - gitlab
      - docker-hub
```

`type`: can be one of
- `docker-build`

# type-specific parameters

## `docker-build`

**notes**
- if the commit has a (semver-compliant) tag associated with it, the image will have the following labels
  - `latest`
  - `x.y.z`
  - `x.y`

- otherwise, the image will have the following labels
  - `<commit-hash>`
