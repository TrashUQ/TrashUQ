from concurrent import futures

import grpc

from app import fl_pb2, fl_pb2_grpc
from app.fl_coordinator import coordinator


class FederatedLearningGrpcService(fl_pb2_grpc.FederatedLearningServiceServicer):
    def Join(self, request: fl_pb2.JoinRequest, context: grpc.ServicerContext) -> fl_pb2.JoinResponse:
        client_id = request.client_id.strip()
        if not client_id:
            return fl_pb2.JoinResponse(ok=False, message="client_id is required")

        round_number, model_version, global_weights = coordinator.join(client_id)
        return fl_pb2.JoinResponse(
            ok=True,
            message="joined",
            round=round_number,
            model_version=model_version,
            global_weights=global_weights,
        )

    def GetGlobalModel(
        self, request: fl_pb2.GetGlobalModelRequest, context: grpc.ServicerContext
    ) -> fl_pb2.GetGlobalModelResponse:
        client_id = request.client_id.strip() or "anonymous"
        round_number, model_version, global_weights = coordinator.get_model(client_id)
        return fl_pb2.GetGlobalModelResponse(
            ok=True,
            message="global model fetched",
            round=round_number,
            model_version=model_version,
            global_weights=global_weights,
        )

    def SubmitUpdate(
        self, request: fl_pb2.SubmitUpdateRequest, context: grpc.ServicerContext
    ) -> fl_pb2.SubmitUpdateResponse:
        client_id = request.client_id.strip()
        if not client_id:
            return fl_pb2.SubmitUpdateResponse(ok=False, message="client_id is required")

        round_aggregated, current_round, model_version, message = coordinator.submit_update(
            client_id=client_id,
            round_number=request.round,
            num_samples=request.num_samples,
            local_weights=list(request.local_weights),
            local_loss=request.local_loss,
            local_accuracy=request.local_accuracy,
        )

        return fl_pb2.SubmitUpdateResponse(
            ok=round_aggregated or message.startswith("update accepted"),
            message=message,
            round_aggregated=round_aggregated,
            current_round=current_round,
            model_version=model_version,
        )


class GrpcServerRuntime:
    def __init__(self, host: str, port: int) -> None:
        self._server = grpc.server(futures.ThreadPoolExecutor(max_workers=8))
        fl_pb2_grpc.add_FederatedLearningServiceServicer_to_server(FederatedLearningGrpcService(), self._server)
        self._server.add_insecure_port(f"{host}:{port}")

    def start(self) -> None:
        self._server.start()

    def stop(self, grace: float = 2.0) -> None:
        self._server.stop(grace)
