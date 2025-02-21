# Docker Deploy

For the docker deployment pipeline, repositories require a certain structure. See [deployments](https://gitlab.com/haondt/deployments) for an example. It is structured in such a way that many services can be added without being overly repetitive or lost in giant docker files. This is achieved by segmenting services into seperate docker files, and combining them back together with a python script. The structure is more clearly defined below:

## 1. Projects

The base directory of the repository should contain one directory for each deployment project. The rest of this document is relative to the directory of the project in question.

## 2. Base files

At the root of the directory there can be some project-level configuration files:

#### `docker-compose-base.haondt.yml`

This file contains a single service definition. When loading a `docker-compose.yml` file from a service, each container in the file (i.e. `services.*`) will be joined with this base service.
The value `{{ COM_HAONDT_CONTAINER }}` will be replaced with the name of the container from the service. For example, given the following `docker-compose-base.haondt.yml`:

```yml
services:
  {{ COM_HAONDT_CONTAINER }}:
    environment:
      PGID: 1000
    volumes:
      - vol1:/data
```

And the following docker compose file at `services/foo/docker-compose.yml`:

```yml
services:
  foo-service:
    environment:
      PUID: 800
      PGID: 900
    depends-on:
      - bar
  bar:
```

The final docker compose file will contain:

```yml
services:
  foo-service:
    environment:
      PUID: 800
      PGID: 900
    depends-on:
      - bar
    volumes:
      - vol1:/data
  bar:
    environment:
      PGID: 1000
    volumes:
      - vol1:/data
```

Notice how if a primitive field is provided in both files (e.g. `*.environment.PGID`), the one in the service file will take priority over the base. If the field is an array, it will be merged with the values from both.

#### `config.haondt.yml`

This file provides configuration about the deployment target for the project.

```yaml
name: my-project-name # optional, will default to the project directory name
key: $MY_HOST_SSH_KEY # ssh key for connecting to the project host, can be a file or an env var pointing at a file
target: me@my-host # ssh host for the deployment
```

The project will be deployed to `$target:/srv/deploy/$name`, and the connection will be made using `$key` as the ssh key.

#### `env.haondt.yml`

This is an optional file. It can be used to provide project-wide hydration values for all services.


## 3. Service Files

For each directory in `services/*` that contains a `docker-compose.yml` file, the script will merge its services with `docker-compose-base.haondt.yml` as described above, and then merge it into the final docker compose file.

In the deployment, all the files in the service directory (`services/myservice/*`) will be copied to `/srv/deploy/myproject/myservice/*`, with the exception of the `docker-compose.yml` file and any `*.haondt.yml` files. This means you can reference them in the docker compose for volume mounting like so

**`services/myservice/docker-compose.yml`**

```yml
services:
  mycontainer:
    volumes:
      - ./myservice/some_file.txt:/data/some_file.txt
```

## 4. Hydration

This pipeline also provides a method for hydrating files with values from outside sources. This is good for, for example, populating configuration files with secret data.

### Environment files

To use a value for hydration, it has to be loaded into the hydration environment for the service. The hydration environment provides values for hydration only. **The hydration environment is not at all connected to the service shell environment**.

The `env.haondt.yml` file in the project directory will be loaded into the hydration environment for all services. Additionally, within the base of the service directory, you can provide an additional `env.haondt.yml` file.

### Hydration Mechanism

The actual process of hydration is as follows:

Firstly, the hydration environment is created by [flattening](#flattening) the keys of the hydration files, and the values are loaded with [plugin](#plugins) support.

When hydrating a file, any appearances of the string `{{ my__flattened__key }}` will be replaced with corresponding value from the hydration environment. An example:

**`env.haondt.yml`**

```yml
tokens:
    foo: mytoken
    bar: mytoken2
    dyn: mytoken3
host: myhost
dynamic_service: baz
```

My file to be hydrated: **`config.toml`**

```toml
[client]
host = "{{ host }}"

[client.services.foo]
password = "{{ tokens__foo }}"

[client.services.bar]
password = "{{ tokens__bar }}"

[client.services.{{ dynamic_service }}]
password = "{{ tokens__dyn }}"
```

The final **`config.toml`** on the deployment target:

```toml
[client]
host = "myhost"

[client.services.foo]
password = "mytoken"

[client.services.bar]
password = "mytoken2"

[client.services.baz]
password = "mytoken3"
```

The services `docker-compose.yml` file will be hydrated, along with any files listed in the hydration file, which is a file called `hydrate.haondt.yml` placed in the root of the service directory. The hydration file should contain a list of files, with paths relative to the root of the service directory.

### Plugins

A hydration value can be written as `{{ plugin_name('argument1', 'argument2', ...) }}`. In this case, a plugin engine will run and try to resolve the plugin, and use that for the value. Plugins are only supported inside `env.haondt.yml` files. To use them to provide environment variables in the docker compose file, first map the plugin to the hydration environment, then hydrate the environment variable in the docker compose file (or by hydrating a `.env` file and passing that to docker composes `env_file`).

The following plugins are supported:
- `{{ secret('path/to/folder', 'SECRET_NAME') }}` - this will make an api request to Infisical to try and retrieve the secret. It requires the following env vars:
  - `INFISICAL_SECRET_KEY` - the bearer token for infisical
  - `INFISICAL_URL` - the base url for infisical
- `{{ gsm('SECRET_NAME', 'secret_tag1', 'secret_tag2', ...) }}` - this will make an api request to [Gabbro Secret Manager](https://gitlab.com/haondt/gabbro-secret-manager) to try and retrieve the secret. It requires the following env vars:
  - `GSM_API_KEY` - the bearer token for gabbro secret manager
  - `GSM_URL` - the base url for gabbro secret manager
  - it will retrieve a secret that has the matching name and all of the tags. this must result in **exactly one** secret in the response from GSM.
- `{{ env('MY_ENV_VAR') }}` - this will be replaced with the value of the environment variable
- `{{ yaml('PATH', 'foo', 'bar', 0, 'baz')}}` - this will get the yaml file at `PATH` and will use the remaning values to extract a value from the yaml object
  - `PATH` can be a file path or an environment variable that resolves to a file path, with priority on the latter.
  - the remaning arguments must be strings or ints
  - the object that the path resolves to must be a string

## 5. Transformation

A file called `transform.haondt.yml` may also be included in the service directory. This file contains yaml data in the following format:

```yml
- src:
    path: website.env.yml
    type: yaml
    hydrate: true # optional, default is false
  dst:
    path: website.env
    type: env
    separator: "_" # optional, default is "__"
```

For each list item in the yaml file, a source and destination path are given (relative to the service directory). Based on the type, the source file data will be converted, and placed in the `dst` file. The `src` file will not be copied to the output directory.

Supported `src` types:
- `yaml`
- `json`

Supported `dst` types:
- `yaml`
- `json`
- `env` - all values will be [flattened](#flattening) and converted to strings

### Options

- `src.hydrate` - if set to `true`, the source file will be hydrated before transforming it
- `dst.separator` - if set, will override the default separator for the flattening process


## 6. Final Steps

Once everything has been hydrated, transformed and merged into the final docker compose file, the build step will take the whole bundle, tar it, encrypt it and place it in `build.enc`. Then the deployment step will grab it, decrypt it and ship it off to the host.

# Flattening

In some cases data may be flattened from a nesting format (e.g. `yaml`, `json`) to a flattenned format (e.g. `.env`). In these cases, the convention more or less follows the [`ASP.NET` flattening format](https://learn.microsoft.com/en-us/aspnet/core/fundamentals/configuration/?view=aspnetcore-8.0#naming-of-environment-variables). That is to say, the following two formats would be interchangeable:

```json
{
    "SmtpServer": "smtp.example.com",
    "Logging": [
        {
            "Name": "ToEmail",
            "Level": "Critical",
            "Args": {
                "FromAddress": "MySystem@example.com",
                "ToAddress": "SRE@example.com"
            }
        },
        {
            "Name": "ToConsole",
            "Level": "Information"
        }
    ]
}
```

```env
SmtpServer="smtp.example.com"
Logging__0__Name="ToEmail"
Logging__0__Level="Critical"
Logging__0__Args__FromAddress="MySystem@example.com"
Logging__0__Args__ToAddress="SRE@example.com"
Logging__1__Name="ToConsole"
Logging__1__Level="Information"
```

