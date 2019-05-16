""" Extra Handlers that can handle structured LogRecords.
"""
import logging
import pickle
from pathlib import Path

try:
    from torch.utils.tensorboard import SummaryWriter
except ModuleNotFoundError:
    pass


__all__ = ["PickleHandler", "TensorboardHandler"]


class PickleHandler(logging.Handler):
    """ A Handler that writes `logging.LogRecord`s to pickle files.
    TODO: Check the performance?
    """

    def __init__(self, log_dir):
        logging.Handler.__init__(self)
        self.log_dir = log_dir

    def emit(self, record):
        data = self._maybe_load(record.name)

        # these functions mutate `data`!
        if isinstance(record.msg, str):
            self._add_text(record, data)
        elif isinstance(record.msg, dict):
            self._add_scalars(record, data)
        else:
            raise TypeError("PickleHandler receives either a string or a dict.")

        self._save(record.name, data)

    def _maybe_load(self, logger_name):
        """ For commodity reasons we create a pickle file per logger.
            If a pickle exists it will be loaded in memory.
        """
        file_name = logger_name.replace(".", "_")
        file_path = Path(self.log_dir, f"{file_name}.pkl")

        try:
            with open(file_path, "rb") as f:
                return pickle.load(f)
        except FileNotFoundError:
            return {}

    def _save(self, logger_name, data):
        file_name = logger_name.replace(".", "_")
        file_path = Path(self.log_dir, f"{file_name}.pkl")

        with open(file_path, "wb") as f:
            pickle.dump(data, f)

    def _add_text(self, record, data):
        if "text" in data:
            data["text"].append(record.msg)
        else:
            data["text"] = [record.msg]

    def _add_scalars(self, record, data):
        try:
            step = record.msg["step"]
        except Exception as err:
            raise (
                AttributeError(
                    "SummaryWriterHandler expects a LogRecord.msg with a "
                    + "`step` field. Rest of the Exception: "
                    + str(err)
                )
            )
        for k, v in record.msg.items():
            if k != "step":
                entry = {"step": step, "value": v, "time": record.created}
                if k in data:
                    data[k].append(entry)
                else:
                    data[k] = [entry]


class TensorboardHandler(logging.Handler):
    """ A Handler using the Tensorboard SummaryWritter.
    """
    def __init__(self, log_dir):
        logging.Handler.__init__(self)
        self.log_dir = log_dir
        try:
            self.writer = SummaryWriter(log_dir)
        except NameError as err:
            raise NameError(
                "PyTorch >= 1.1.0 is required for logging to Tensorboard."
                + str(err)
            )

    def emit(self, record):
        if isinstance(record.msg, str):
            self._add_text(record)
        elif isinstance(record.msg, dict):
            self._add_scalars(record)
        else:
            raise TypeError(
                "TensorboardHandler receives either a string or a dict."
            )

    def _add_text(self, record):
        rec_name = record.name.replace(".", "/")
        self.writer.add_text(rec_name, record.msg)

    def _add_scalars(self, record):
        rec_name = record.name.replace(".", "/")
        try:
            step = record.msg["step"]
        except Exception as err:
            raise (
                AttributeError(
                    "SummaryWriterHandler expects a LogRecord.msg with a "
                    + "`step` field. Rest of the Exception: "
                    + str(err)
                )
            )
        for k, v in record.msg.items():
            if k != "step":
                self.writer.add_scalar(f"{rec_name}/{k}", v, global_step=step)

    def close(self):
        self.writer.close()
