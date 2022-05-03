import agate
import re
from botocore.exceptions import ClientError
from typing import Optional
from threading import Lock

from dbt.adapters.base import available
from dbt.adapters.sql import SQLAdapter
from dbt.adapters.athena import AthenaConnectionManager
from dbt.adapters.athena.relation import AthenaRelation
from dbt.adapters.athena.utils import get_boto3_session
from dbt.events import AdapterLogger
import dbt.exceptions

logger = AdapterLogger("Athena")
boto3_client_lock = Lock()


class AthenaAdapter(SQLAdapter):
    ConnectionManager = AthenaConnectionManager
    Relation = AthenaRelation

    @classmethod
    def date_function(cls) -> str:
        return "now()"

    @classmethod
    def convert_text_type(cls, agate_table: agate.Table, col_idx: int) -> str:
        return "string"

    @classmethod
    def convert_number_type(cls, agate_table: agate.Table, col_idx: int) -> str:
        decimals = agate_table.aggregate(agate.MaxPrecision(col_idx))
        return "double" if decimals else "integer"

    @classmethod
    def convert_datetime_type(cls, agate_table: agate.Table, col_idx: int) -> str:
        return "timestamp"

    @available
    def get_creds(self):
        conn = self.connections.get_thread_connection()
        creds = conn.credentials
        return creds

    def split_s3_path(self, s3_path):
        splitter = s3_path.replace("s3://", "").split("/")
        bucket = splitter.pop(0)
        prefix = "/".join(splitter)
        return bucket, prefix

    def s3_path_exists(self, s3_path, s3_client):
        bucket, prefix = self.split_s3_path(s3_path)
        result = s3_client.list_objects(Bucket=bucket, Prefix=prefix)
        return True if "Contents" in result else False

    @available
    def delete_s3_object(self, s3_path):
        bucket, prefix = self.split_s3_path(s3_path)

        creds = self.get_creds()
        boto3_session = get_boto3_session(creds.region_name, creds.aws_profile_name)
        s3_client = boto3_session.client("s3")
        s3_resource = boto3_session.resource("s3")

        if self.s3_path_exists(s3_path, s3_client):
            logger.info(f"Delete objects from bucket={bucket}, prefix={prefix}")
            s3_resource.Bucket(bucket).objects.filter(Prefix=prefix).delete()

    @available
    def s3_table_location(self, schema_name: str, table_name: str) -> str:
        creds = self.get_creds()
        if creds.s3_data_dir is not None:
            s3_path = creds.s3_data_dir.format(
                schema_name=schema_name, table_name=table_name
            )
            return s3_path
        else:
            raise ValueError("s3_data_dir is required for the profile config")

    @available
    def clean_up_partitions(
        self, database_name: str, table_name: str, where_condition: str
    ):
        # Look up Glue partitions & clean up
        creds = self.get_creds()
        boto3_session = get_boto3_session(creds.region_name, creds.aws_profile_name)

        with boto3_client_lock:
            glue_client = boto3_session.client("glue")

        s3_resource = boto3_session.resource("s3")
        partitions = glue_client.get_partitions(
            # CatalogId='123456789012', # Need to make this configurable if it is different from default AWS Account ID
            DatabaseName=database_name,
            TableName=table_name,
            Expression=where_condition,
        )
        p = re.compile("s3://([^/]*)/(.*)")
        for partition in partitions["Partitions"]:
            logger.debug(
                "Deleting objects for partition '{}' at '{}'",
                partition["Values"],
                partition["StorageDescriptor"]["Location"],
            )
            m = p.match(partition["StorageDescriptor"]["Location"])
            if m is not None:
                bucket_name = m.group(1)
                prefix = m.group(2)
                s3_bucket = s3_resource.Bucket(bucket_name)
                s3_bucket.objects.filter(Prefix=prefix).delete()

    @available
    def clean_up_table(self, database_name: str, table_name: str):
        # Look up Glue partitions & clean up
        creds = self.get_creds()
        boto3_session = get_boto3_session(creds.region_name, creds.aws_profile_name)

        with boto3_client_lock:
            glue_client = boto3_session.client("glue")

        try:
            table = glue_client.get_table(DatabaseName=database_name, Name=table_name)
        except ClientError as e:
            if e.response["Error"]["Code"] == "EntityNotFoundException":
                logger.debug("Table '{}' does not exists - Ignoring", table_name)
                return

        if table is not None:
            logger.debug(
                "Deleting table data from'{}'",
                table["Table"]["StorageDescriptor"]["Location"],
            )
            p = re.compile("s3://([^/]*)/(.*)")
            m = p.match(table["Table"]["StorageDescriptor"]["Location"])
            if m is not None:
                bucket_name = m.group(1)
                prefix = m.group(2)
                s3_resource = boto3_session.resource("s3")
                s3_bucket = s3_resource.Bucket(bucket_name)
                s3_bucket.objects.filter(Prefix=prefix).delete()

    @available
    def quote_seed_column(self, column: str, quote_config: Optional[bool]) -> str:
        return super().quote_seed_column(column, False)

    @available
    def drop_relation(self, relation):
        if relation.type is None:
            dbt.exceptions.raise_compiler_error(
                "Tried to drop relation {}, but its type is null.".format(relation)
            )

        self.cache_dropped(relation)
        self.execute_macro("drop_relation", kwargs={"relation": relation})

        # Remove data along on S3
        s3_path = self.s3_table_location(relation.schema, relation.identifier)
        self.delete_s3_object(s3_path)
