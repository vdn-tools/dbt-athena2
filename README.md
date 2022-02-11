# dbt-athena2
This is a adapter leveraged from [this repo](https://github.com/Tomme/dbt-athena) to better serve our custom needs. It supports addtional capabilitis as below:
- Run on dbt-core version 1.0.x
- Support boto3 session to take the credential from from aws profile name
- On schema change support for new columns added
- Add s3 bucket for storing data instead of randomly writing on staging dir

## Quick started
Within your python environment, proceed below step to initate a first project. There will be some prompts at during inital steps, refer `Configuring your profile` section below to properly set it up.

```bash
pip install dbt-athena2
dbt init my_dbt_project
export DBT_PROFILES_DIR=`pwd`
cd my_dbt_project
dbt debug # to test connection
dbt seed # to dump your seed data
dbt run # to run all models
dbt run --select model_name # to run specific model

#...and more...
```

## Basic usage
### Model configuration
Below show an example how we configure how our model be configured.
- There are 4 supported `materialized` modes: `view`, `table`, `incremental` and `esphemeral`. Details [here](https://docs.getdbt.com/docs/building-a-dbt-project/building-models/materializations).
- `incremental_strategy` supports `insert_overwrite` and `append`. If partition is specified, it only overwrites partions available from source data.
- `on_schema_change` support `fail`, `ignore` and `append_new_columns` only and for only `incremental` materialization. Details [here](https://docs.getdbt.com/docs/building-a-dbt-project/building-models/configuring-incremental-models#understanding-the-is_incremental-macro).
- There are some usefule macro such as `run_started_at` can be referred from [here](https://docs.getdbt.com/reference/dbt-jinja-functions) to enhance the flexibility on the model.

```yaml
{{ config(
    materialized="incremental",
    partitioned_by=["report_month"],
    incremental_strategy="insert_overwrite",
    on_schema_change="append_new_columns"
) }}

{% set run_date = run_started_at.astimezone(modules.pytz.timezone("Asia/Saigon")).strftime("%Y-%m-%d") %}

select cast(working_day as timestamp) working_day,
sum(spend_balance) spend_balance,
sum(td_balance) td_balance,
sum(gs_balance) gs_balance,
cast(date_format(date_parse('{{ run_date }}', '%Y-%m-%d') - interval '1' month, '%Y%m') as int) report_month
from {{ source('analytics', 'eod_balance') }}
where cast(working_day as date) >= date_trunc('month', cast(date_parse('{{ run_date }}', '%Y-%m-%d')  as date)-interval'2'month)
and cast(working_day as date) < date_trunc('month', cast(date_parse('{{ run_date }}', '%Y-%m-%d')  as date)-interval'1'month)
group by working_day
order by working_day desc
```

### Seed
Under folder seeds, place csv seed file ( eg. `c_ecom_rate.csv`) and the yaml config (eg. `c_ecom_rate.yml`) as below example. Then run `dbt seed`

```yaml
version: 2

seeds:
  - name: c_ecom_rate
    config:
      enabled: true
      quote_columns: true
      tags: accounting | report
```

## Further notes
- If the workgroup is specified in the `profile.yml` without `s3_staging_dir`, it will extract the default s3 ouput attached with that [`work_group when Override client-side settings enabled`](https://docs.aws.amazon.com/athena/latest/ug/workgroups-settings-override.html).

- The boto3 session inherit from devlopment environment; once deployed, it should be obtained permission as role such as EC2 profile instance or K8S service account role.

- Athena limit ALTER ADD COLUMNS with data type `date`, recommend to parse it to `timestamp` or `string` during implementing the model. Details [here](https://docs.aws.amazon.com/athena/latest/ug/alter-table-add-columns.html).

- Athena not accept the comment like `/*`, to ignore these auto generated comment from `dbt`, place this `query-comment: null` in `dbt_project.yml` file.

## Configuring your profile

A dbt profile can be configured to run against AWS Athena using the following configuration:

| Option          | Description                                                                     | Required?  | Example               |
|---------------- |-------------------------------------------------------------------------------- |----------- |---------------------- |
| s3_staging_dir  | S3 location to store Athena query results and metadata                          | Required   | `s3://athena-output-bucket/data_services/`    |
| region_name     | AWS region of your Athena instance                                              | Required   | `ap-southeast-1`           |
| schema          | Specify the schema (Athena database) to build models into (lowercase **only**)  | Required   | `dbt`                 |
| database        | Specify the database (Data catalog) to build models into (lowercase **only**)   | Required   | `awsdatacatalog`      |
| poll_interval   | Interval in seconds to use for polling the status of query results in Athena    | Optional   | `5`                   |
| aws_profile_name| Profile to use from your AWS shared credentials file.                           | Optional   | `my-profile`          |
| work_group      | Identifier of Athena workgroup                                                  | Optional   | `my-custom-workgroup` |
| num_retries     | Number of times to retry a failing query                                        | Optional   | `3`                   |
| s3_data_dir     | Prefix for storing tables, if different from the connection's `s3_staging_dir`  | Optional   | `s3://athena-data-bucket/{schema_name}/{table_name}/`   |

**Example profiles.yml entry:**
```yaml
athena:
  target: dev
  outputs:
    dev:
      database: awsdatacatalog
      region_name: ap-southeast-1
      aws_profile_name: dl-dev-process
      s3_staging_dir: s3://athena-output-bucket/data_services/
      s3_data_dir: s3://athena-data-bucket/{schema_name}/{table_name}/
      schema: accounting
      type: athena
```

_Additional information_
* `threads` is supported
* `database` and `catalog` can be used interchangeably

### Running tests

First, install the adapter and its dependencies using `make` (see [Makefile](Makefile)):

```bash
make install_deps
```

Next, configure the environment variables in [dev.env](dev.env) to match your Athena development environment. Finally, run the tests using `make`:

```bash
make run_tests
```

## References
- [How to structure a dbt project](https://discourse.getdbt.com/t/how-we-structure-our-dbt-projects/355)
- [dbt best practices](https://docs.getdbt.com/docs/guides/best-practices)