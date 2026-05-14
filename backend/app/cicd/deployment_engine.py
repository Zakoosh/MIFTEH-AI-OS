from __future__ import annotations
from datetime import datetime
from pathlib import Path
import json
from .models import Deployment, DeploymentStatus, Environment, RolloutStrategy
from .staging_manager import StagingManager
from .release_tracking import ReleaseTracking
from .rollback_deployments import RollbackDeployments
from .build_validation import BuildValidation
from .deployment_monitor import DeploymentMonitor


MEMORY_DIR = Path(__file__).parent.parent / "memory" / "cicd"


class DeploymentEngine:
    PRODUCTION_REQUIRES_APPROVAL = True

    def __init__(self):
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        self._deployments_path = MEMORY_DIR / "deployments.json"
        self.staging = StagingManager()
        self.releases = ReleaseTracking()
        self.rollbacks = RollbackDeployments()
        self.build_validation = BuildValidation()
        self.monitor = DeploymentMonitor()

    def _load(self) -> list[dict]:
        if not self._deployments_path.exists():
            return []
        try:
            return json.loads(self._deployments_path.read_text())
        except Exception:
            return []

    def _save(self, data: list[dict]) -> None:
        self._deployments_path.write_text(json.dumps(data, indent=2, default=str))

    def _persist(self, deployment: Deployment) -> None:
        data = self._load()
        for i, d in enumerate(data):
            if d["id"] == deployment.id:
                data[i] = deployment.model_dump()
                self._save(data)
                return
        data.append(deployment.model_dump())
        self._save(data)

    def create_deployment(
        self,
        project_id: str,
        environment: Environment,
        version: str,
        strategy: RolloutStrategy = RolloutStrategy.blue_green,
        triggered_by: str = "manual",
        notes: str = "",
    ) -> dict:
        is_prod = environment == Environment.production or environment == "production"
        if is_prod and self.PRODUCTION_REQUIRES_APPROVAL:
            deployment = Deployment(
                project_id=project_id,
                environment=environment,
                version=version,
                strategy=strategy,
                status=DeploymentStatus.awaiting_approval,
                triggered_by=triggered_by,
                approval_required=True,
                notes=notes,
            )
            self._persist(deployment)
            return {
                "success": True,
                "deployment": deployment.model_dump(),
                "message": "Deployment created — awaiting manual approval before production deploy",
                "requires_approval": True,
            }

        validation = self.build_validation.validate_build(project_id, version)
        if not validation["passed"]:
            return {"success": False, "error": "Build validation failed", "details": validation}

        deployment = Deployment(
            project_id=project_id,
            environment=environment,
            version=version,
            strategy=strategy,
            status=DeploymentStatus.building,
            triggered_by=triggered_by,
            approval_required=False,
            started_at=datetime.utcnow(),
            notes=notes,
        )
        self._persist(deployment)
        return {
            "success": True,
            "deployment": deployment.model_dump(),
            "message": f"Deployment to {environment} initiated",
            "requires_approval": False,
        }

    def list_deployments(self, project_id: str | None = None, environment: str | None = None, status: str | None = None) -> list[dict]:
        data = self._load()
        if project_id:
            data = [d for d in data if d.get("project_id") == project_id]
        if environment:
            data = [d for d in data if d.get("environment") == environment]
        if status:
            data = [d for d in data if d.get("status") == status]
        return sorted(data, key=lambda x: x.get("id", ""), reverse=True)

    def get_deployment(self, deployment_id: str) -> dict | None:
        for d in self._load():
            if d["id"] == deployment_id:
                return d
        return None

    def get_system_status(self) -> dict:
        all_deployments = self._load()
        active = [d for d in all_deployments if d.get("status") in ("building", "staging", "deploying", "awaiting_approval")]
        prod_deploys = [d for d in all_deployments if d.get("environment") == "production" and d.get("status") == "deployed"]
        last_prod = prod_deploys[-1].get("completed_at") if prod_deploys else None
        return {
            "status": "operational",
            "active_pipelines": 0,
            "active_deployments": len(active),
            "staging_deployments": len(self.staging.list_staging()),
            "last_production_deploy": last_prod,
            "safety_mode": True,
            "auto_deploy_to_production": False,
        }
