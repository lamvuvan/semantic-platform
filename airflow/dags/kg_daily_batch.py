"""DAG chính: nạp dữ liệu daily batch vào Knowledge Graph.

Lịch chạy 02:00 mỗi ngày. Idempotent theo `logical_date`.
Tham chiếu: docs/PLAN.md §2.5
"""
from __future__ import annotations

import pendulum
from airflow.decorators import dag, task_group
from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator  # noqa: F401  (placeholder; thực tế dùng BashOperator/SSHOperator)
from airflow.operators.bash import BashOperator
from airflow.operators.empty import EmptyOperator

DEFAULT_ARGS = {
    "owner": "semantic-platform",
    "retries": 2,
    "retry_delay": pendulum.duration(minutes=5),
}

ENV = {
    "NEO4J_URI": "{{ var.value.neo4j_uri }}",
    "NEO4J_USER": "{{ var.value.neo4j_user }}",
    "NEO4J_PASSWORD": "{{ var.value.neo4j_password }}",
    "S3_ENDPOINT": "{{ var.value.s3_endpoint }}",
    "S3_ACCESS_KEY": "{{ var.value.s3_access_key }}",
    "S3_SECRET_KEY": "{{ var.value.s3_secret_key }}",
}


@dag(
    dag_id="kg_daily_batch",
    description="Daily batch load vào Knowledge Graph",
    schedule="0 2 * * *",
    start_date=pendulum.datetime(2026, 4, 1, tz="Asia/Ho_Chi_Minh"),
    catchup=False,
    default_args=DEFAULT_ARGS,
    tags=["semantic-platform", "kg"],
)
def kg_daily_batch() -> None:
    start = EmptyOperator(task_id="start")
    end = EmptyOperator(task_id="end")

    backup = BashOperator(
        task_id="neo4j_backup_snapshot",
        bash_command=(
            "neo4j-admin database backup neo4j "
            "--to-path=s3://kg-backups/dt={{ ds }}/"
        ),
    )

    @task_group(group_id="transform")
    def transform() -> None:
        BashOperator(
            task_id="dbt_run",
            bash_command="cd /opt/transforms/dbt && dbt run --target prod --select state:modified+",
        )
        BashOperator(
            task_id="spark_export_csv",
            bash_command=(
                "spark-submit --master spark://spark-master:7077 "
                "/opt/transforms/spark/jobs/export_kg_csv.py "
                "--gold-db semantic_platform "
                "--output s3a://kg-staging/dt={{ ds }}/"
            ),
        )

    @task_group(group_id="load_nodes")
    def load_nodes() -> None:
        for entity in ["merchant", "category", "product", "product_variant", "topping", "customer", "order", "order_line"]:
            BashOperator(
                task_id=f"load_{entity}",
                bash_command=(
                    f"python -m loaders.nodes.load_{entity} "
                    f"--bucket kg-staging --prefix dt={{{{ ds }}}}/kg_nodes_{entity}/"
                ),
                env=ENV,
            )

    @task_group(group_id="load_edges")
    def load_edges() -> None:
        BashOperator(
            task_id="load_master_edges",
            bash_command=(
                "python -m loaders.edges.load_master_edges "
                "--bucket kg-staging --prefix-base dt={{ ds }}/"
            ),
            env=ENV,
        )
        BashOperator(
            task_id="load_order_lines",
            bash_command=(
                "python -m loaders.edges.load_order_lines "
                "--bucket kg-staging --prefix-base dt={{ ds }}/"
            ),
            env=ENV,
        )

    embed = BashOperator(
        task_id="compute_embeddings",
        bash_command=(
            "spark-submit --master spark://spark-master:7077 "
            "/opt/transforms/spark/jobs/embed_products.py "
            "--gold-db semantic_platform "
            "--output s3a://kg-staging/embeddings/dt={{ ds }}/"
        ),
    )

    load_embeddings = BashOperator(
        task_id="load_embeddings",
        bash_command=(
            "python -m loaders.embeddings.load_product_embeddings "
            "--bucket kg-staging --prefix embeddings/dt={{ ds }}/"
        ),
        env=ENV,
    )

    derive = BashOperator(
        task_id="derive_edges",
        bash_command="python -m loaders.post_process.derive_edges",
        env=ENV,
    )

    smoke = BashOperator(
        task_id="smoke_check",
        bash_command="python -m tests.smoke.kg_counts --baseline /opt/baselines/{{ ds }}.json",
    )

    start >> backup >> transform() >> load_nodes() >> load_edges() >> embed >> load_embeddings >> derive >> smoke >> end


kg_daily_batch()
