from locust import HttpUser, task, between

class EnterpriseDataAnalystUser(HttpUser):
    wait_time = between(1, 3)
    token = None

    def on_start(self):
        # 1. Register a test user (fails safely if user exists)
        self.client.post("/api/v1/auth/register", json={
            "email": "locust_perf_user@example.com",
            "password": "Password123!",
            "full_name": "Locust Perf User"
        })

        # 2. Login to get JWT Token
        res = self.client.post("/api/v1/auth/login", data={
            "username": "locust_perf_user@example.com",
            "password": "Password123!"
        })
        if res.status_code == 200:
            self.token = res.json().get("access_token")

    @task(3)
    def check_telemetry(self):
        if not self.token:
            return
        headers = {"Authorization": f"Bearer {self.token}"}
        # Hit Cache stats
        self.client.get("/api/v1/cache/stats", headers=headers)
        # Hit performance telemetry stats
        self.client.get("/api/v1/performance", headers=headers)

    @task(2)
    def fetch_datasets(self):
        if not self.token:
            return
        headers = {"Authorization": f"Bearer {self.token}"}
        # Hit dataset query list
        self.client.get("/api/v1/datasets/", headers=headers)

    @task(1)
    def execute_upload_lifecycle(self):
        if not self.token:
            return
        headers = {"Authorization": f"Bearer {self.token}"}
        
        # Simulates small dataset uploads
        csv_payload = "id,name,salary\n1,Developer,80000\n2,Manager,100000\n3,Designer,70000"
        files = {
            "file": ("locust_journey.csv", csv_payload, "text/csv")
        }
        upload_res = self.client.post("/api/v1/datasets/upload", files=files, headers=headers)
        if upload_res.status_code == 200:
            dataset_id = upload_res.json().get("id")
            
            # Request profile info
            self.client.get(f"/api/v1/datasets/{dataset_id}/profile", headers=headers)
            
            # Request auto insights
            self.client.get(f"/api/v1/datasets/{dataset_id}/insights", headers=headers)
            
            # Request default dashboard layout
            self.client.get(f"/api/v1/datasets/{dataset_id}/dashboard", headers=headers)
            
            # Drop dataset to clean up disk footprint
            self.client.delete(f"/api/v1/datasets/{dataset_id}", headers=headers)
