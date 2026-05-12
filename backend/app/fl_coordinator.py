import threading
from dataclasses import dataclass

from app.config import settings


@dataclass
class ClientUpdate:
    client_id: str
    num_samples: int
    local_weights: list[float]
    local_loss: float
    local_accuracy: float


class FederatedCoordinator:
    def __init__(self, model_size: int = 16, min_clients: int = 2) -> None:
        self.model_size = model_size
        self.min_clients = max(1, min_clients)
        self._lock = threading.Lock()
        self._online_clients: set[str] = set()
        self._round = 1
        self._model_version = 1
        self._global_weights = [0.0] * model_size
        self._round_updates: dict[str, ClientUpdate] = {}

    def join(self, client_id: str) -> tuple[int, int, list[float]]:
        with self._lock:
            self._online_clients.add(client_id)
            return self._round, self._model_version, self._global_weights.copy()

    def get_model(self, client_id: str) -> tuple[int, int, list[float]]:
        with self._lock:
            self._online_clients.add(client_id)
            return self._round, self._model_version, self._global_weights.copy()

    def submit_update(
        self,
        client_id: str,
        round_number: int,
        num_samples: int,
        local_weights: list[float],
        local_loss: float,
        local_accuracy: float,
    ) -> tuple[bool, int, int, str]:
        if round_number <= 0:
            return False, self._round, self._model_version, "round must be >= 1"
        if num_samples <= 0:
            return False, self._round, self._model_version, "num_samples must be > 0"
        if len(local_weights) != self.model_size:
            return (
                False,
                self._round,
                self._model_version,
                f"local_weights must have length {self.model_size}",
            )

        with self._lock:
            self._online_clients.add(client_id)

            if round_number != self._round:
                return (
                    False,
                    self._round,
                    self._model_version,
                    f"stale round {round_number}; current round is {self._round}",
                )

            self._round_updates[client_id] = ClientUpdate(
                client_id=client_id,
                num_samples=num_samples,
                local_weights=local_weights,
                local_loss=local_loss,
                local_accuracy=local_accuracy,
            )

            if len(self._round_updates) < self.min_clients:
                return False, self._round, self._model_version, "update accepted; waiting for more clients"

            self._aggregate_round_locked()
            return True, self._round, self._model_version, "round aggregated"

    def _aggregate_round_locked(self) -> None:
        total_samples = sum(update.num_samples for update in self._round_updates.values())
        if total_samples <= 0:
            total_samples = len(self._round_updates)

        new_weights = [0.0] * self.model_size
        for update in self._round_updates.values():
            weight = update.num_samples / total_samples
            for i, value in enumerate(update.local_weights):
                new_weights[i] += value * weight

        self._global_weights = new_weights
        self._model_version += 1
        self._round += 1
        self._round_updates.clear()


coordinator = FederatedCoordinator(
    model_size=settings.fl_model_size,
    min_clients=settings.fl_min_clients_per_round,
)
