import abc

class ResetProtocol(abc.ABC):
    @abc.abstractmethod
    def reset(self):
        raise NotImplementedError

    @abc.abstractmethod
    def set_reset_enable(self, enable):
        raise NotImplementedError
