"""Theses classes are just to keep memory and cpu sizes,
every method in them is just to speed something up or
to keep the code little bit more readable."""


def empty_copy(obj):
    """This is here just to omit the __init__ during copy."""
    class Empty(obj.__class__):
        def __init__(self):
            pass
    newcopy = Empty()
    newcopy.__class__ = obj.__class__
    return newcopy


class instance_capacity:
    def __init__(self, memory=0, cpu=0, container_instance_id=""):
        self.cpu = int(cpu)
        self.memory = int(memory)
        self.instance_id = ""
        self.container_instance_id = container_instance_id

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return "id:" + self.container_instance_id + " cpu:" + str(self.cpu) + " mem:" + str(self.memory)

    def __eq__(self, other):
        return self.container_instance_id == other.container_instance_id

    def __copy__(self, memodict={}):
        copy_object = empty_copy(self)
        copy_object.cpu = self.cpu
        copy_object.memory = self.memory
        copy_object.instance_id = self.instance_id
        copy_object.container_instance_id = self.container_instance_id
        return copy_object


class task_capacity:
    def __init__(self, memory=0, cpu=0, container_instance_id="", task_arn=""):
        self.cpu = int(cpu)
        self.memory = int(memory)
        self.container_instance_id = container_instance_id
        self.task_arn = task_arn

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return "container_instance_id: " + self.container_instance_id + " cpu:" + str(self.cpu) + " mem:" + str(self.memory)

    def __eq__(self, other):
        return self.task_arn == other.task_arn

    def __copy__(self, memodict={}):
        copy_object = empty_copy(self)
        copy_object.cpu = self.cpu
        copy_object.memory = self.memory
        copy_object.task_arn = self.task_arn
        copy_object.container_instance_id = self.container_instance_id
        return copy_object
