from abc import ABC, abstractmethod

from inference_service.schemas.inference import InferenceRequest


class BaseInferenceAdapter(ABC):
    @abstractmethod
    def describe(self):
        raise NotImplementedError

    @abstractmethod
    def detect(self, payload: InferenceRequest):
        raise NotImplementedError
