import os.path
import re

from compliance_checker.base import CallableCheckBase, Result, Dataset, GenericFile


def _get_file_size(fpath):
    "Returns size of file (in bytes)."
    return os.path.getsize(fpath)


def _is_file_size_less_than(fpath, n):
    """
    Checks file size of `fpath` and returns True if its size is less than `n` MBs.

    :param fpath: file path [string]
    :param n: size in Mbytes [float]
    :return: boolean
    """
    n = float(n)
    size_in_mbs = _get_file_size(fpath) / (2.**20)

    if size_in_mbs <= n:
        return True

    return False


class FileCheckBase(CallableCheckBase):
    "Base class for all File Checks (that work on a file path."

    def _check_primary_arg(self, primary_arg):
        if not os.path.isfile(primary_arg):
            raise Exception("File not found: {}".format(primary_arg))

    def __call__(self, primary_arg):
        """
        Make sure primary_arg is a filename
        """
        if isinstance(primary_arg, GenericFile):
            primary_arg = primary_arg.fpath
        elif isinstance(primary_arg, Dataset):
            primary_arg = primary_arg.filepath()

        return super(FileCheckBase, self).__call__(primary_arg)


class FileSizeCheck(FileCheckBase):
    """
    Data file {strictness} size limit: {threshold}Gbytes.
    """
    short_name = "File size {strictness} limit {threshold}Gbytes"
    defaults = {"threshold": 2, "strictness": "hard"}
    message_templates = ["Data file exceeds {strictness} limit of {threshold}Gbytes in size."]
    level = "HIGH"

    def _get_result(self, primary_arg):
        fpath = primary_arg
        threshold = float(self.kwargs["threshold"])

        success = _is_file_size_less_than(fpath, threshold * (2.**30))
        messages = []

        if success:
            score = self.out_of
        else:
            score = 0
            messages.append(self.get_messages()[score])

        return Result(self.level, (score, self.out_of),
                      self.get_short_name(), messages)


class FileNameStructureCheck(FileCheckBase):
    """
    File name must consist of items separated by '{delimiter}', followed by '{extension}'.
    """

    short_name = "File name structure"
    defaults = {"delimiter": "_", "extension": ".nc"}
    message_templates = [
        "File name does not follow required format of '{delimiter}' delimiters and '{extension}' extension."]
    level = "HIGH"

    def _get_result(self, primary_arg):
        fpath = os.path.basename(primary_arg)
        regex = re.compile("[^{delimiter}](\w+{delimiter})+\w+({delimiter}\w+)?\{extension}".format(**self.kwargs))

        success = regex.match(fpath)
        messages = []

        if success:
            score = self.out_of
        else:
            score = 0
            messages.append(self.get_messages()[score])

        return Result(self.level, (score, self.out_of),
                      self.get_short_name(), messages)
