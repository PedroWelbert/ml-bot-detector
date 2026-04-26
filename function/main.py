import functions_framework
import joblib
import pandas as pd
import numpy as np
from google.cloud import storage, logging as cloud_logging
from google.cloud.compute_v1 import InstancesClient
from google.cloud.logging import DESCENDING
import requests
from datetime import datetime, timedelta
import re

BUCKET_NAME = "ml-bot-detector-blog-mba"
MODEL_FILE = "modelo_rf_bot_detector.pkl"
DISCORD_WEBHOOK = "omitido_por_seguranca"
ABUSEIPDB_API_KEY = "omitido_por_seguranca"
PROJECT_ID = "omitido_por_seguranca"
INSTANCE_ID = "omitido_por_seguranca"
ZONE = "omitido_por_seguranca"
PROBABILITY_THRESHOLD = 75
ABUSE_SCORE_THRESHOLD = 50
ABUSEIPDB_URL = "https://api.abuseipdb.com/api/v2/check"
ABUSEIPDB_MAX_AGE_DAYS = "90"


def get_instance_details(project, zone, instance_id):
    client = InstancesClient()
    instance = client.get(project=project, zone=zone, instance=instance_id)

    name = instance.name
    external_ip = ""

    for interface in instance.network_interfaces:
        for config in interface.access_configs:
            if config.nat_i_p:
                external_ip = config.nat_i_p
                break
    return name, external_ip

def check_abuseipdb(ip_address):
    headers = {
        "Accept": "application/json",
        "Key": ABUSEIPDB_API_KEY,
    }
    params = {
        "ipAddress": ip_address,
        "maxAgeInDays": ABUSEIPDB_MAX_AGE_DAYS,
    }

    try:
        response = requests.get(ABUSEIPDB_URL, headers=headers, params=params, timeout=5)
        response.raise_for_status()
        data = response.json().get("data", {})
        return {
            "abuse_confidence_score": data.get("abuseConfidenceScore", 0),
            "total_reports": data.get("totalReports", 0),
            "domain": data.get("domain", "N/A"),
            "country_code": data.get("countryCode", "N/A"),
            "isp": data.get("isp", "N/A"),
        }
    except Exception as e:
        print(f"ABUSEIPDB lookup failed for {ip_address}: {e}")
        return None

@functions_framework.http
def detector_pipeline(request):
    try:
        vm_name, vm_external_ip = get_instance_details(PROJECT_ID, ZONE, INSTANCE_ID)
        excluded_ips = [vm_external_ip, "127.0.0.1"]

        print(f"STARTING PIPELINE: Analyzing VM {vm_name} (IP: {vm_external_ip})")

        storage_client = storage.Client()
        bucket = storage_client.get_bucket(BUCKET_NAME)
        blob = bucket.blob(MODEL_FILE)
        blob.download_to_filename("/tmp/model.pkl")
        model = joblib.load("/tmp/model.pkl")
        training_features = model.feature_names_in_

        log_client = cloud_logging.Client(project=PROJECT_ID)
        start_time = (datetime.utcnow() - timedelta(hours=4)).isoformat() + "Z"
        query_filter = (
            f'resource.type="gce_instance"'
            f' AND resource.labels.instance_id="{INSTANCE_ID}"'
            f' AND timestamp >= "{start_time}"'
        )

        entries = log_client.list_entries(filter_=query_filter, order_by=DESCENDING, max_results=1000)

        logs_data = []
        for entry in entries:
            ip, url, status, size, method = None, "", 200, 0, "GET"
            payload_text = str(entry.payload) if entry.payload else ""

            if payload_text:
                ip_match = re.search(r"(\d+\.\d+\.\d+\.\d+)", payload_text)
                if ip_match:
                    ip = ip_match.group(1)

                if not ip or ip in excluded_ips:
                    continue

                req_match = re.search(r'"([A-Z]+)\s+(/[^\s]*)\s+HTTP', payload_text)
                if req_match:
                    method, url = req_match.group(1), req_match.group(2)

                stat_match = re.search(r'"\s+(\d{3})\s+(\d+|-)', payload_text)
                if stat_match:
                    status = int(stat_match.group(1))
                    size = 0 if stat_match.group(2) == "-" else int(stat_match.group(2))

            if ip:
                extension = url.split(".")[-1].split("?")[0] if "." in url else "no_extension"
                is_suspicious = 1 if any(x in url for x in ["wp-admin", "wp-login", ".env", "xmlrpc", "config"]) else 0

                logs_data.append({
                    "ip": ip,
                    "status": int(status),
                    "size": int(size),
                    "method": str(method),
                    "extension": extension,
                    "is_suspicious_path": is_suspicious,
                })

        if not logs_data:
            return f"Processed: No external logs for {vm_name}.", 200

        df_logs = pd.DataFrame(logs_data)
        ip_summary = df_logs.groupby("ip").agg({
            "status": "median",
            "size": "mean",
            "is_suspicious_path": "max",
            "method": lambda x: x.mode()[0],
            "extension": lambda x: x.mode()[0],
        })
        ip_summary["req_per_minute"] = df_logs.groupby("ip").size()
        ip_summary = ip_summary.reset_index()

        for _, row in ip_summary.iterrows():
            input_df = pd.DataFrame(0, index=[0], columns=training_features)
            input_df["status"] = row["status"]
            input_df["tamanho_num"] = row["size"]
            input_df["req_por_minuto"] = row["req_per_minute"]
            input_df["is_suspicious_path"] = row["is_suspicious_path"]

            for col in [f"extensao_{row['extension']}", f"metodo_{row['method']}"]:
                if col in input_df.columns:
                    input_df[col] = 1

            probability = model.predict_proba(input_df)[0][1] * 100

            if probability > PROBABILITY_THRESHOLD:
                abuse_info = check_abuseipdb(row["ip"])

                if abuse_info is None:
                    print(f"Skipping alert for {row['ip']}: AbuseIPDB lookup failed.")
                    continue

                if abuse_info["abuse_confidence_score"] > ABUSE_SCORE_THRESHOLD:
                    requests.post(DISCORD_WEBHOOK, json={
                        "content": (
                            f"🚨 **Detecção de Bot**\n"
                            f"**Servidor:** `{vm_name}`\n"
                            f"**IP Atacante:** `{row['ip']}`\n"
                            f"**Confiança da IA:** `{probability:.2f}%`\n"
                            f"**Pontuação de Abuso (AbuseIPDB):** `{abuse_info['abuse_confidence_score']}%`\n"
                            f"**Total de Denúncias:** `{abuse_info['total_reports']}`\n"
                            f"**Domínio:** `{abuse_info['domain']}`"
                        )
                    })

        return f"Pipeline para {vm_name} finalizado.", 200

    except Exception as e:
        print(f"FATAL ERROR: {str(e)}")
        return f"Erro: {str(e)}", 500