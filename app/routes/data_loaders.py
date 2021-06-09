from promise import Promise
from promise.dataloader import DataLoader

from app.common.models.icpdao.job import Job
from app.common.models.icpdao.user import User


class BaseModelLoader(DataLoader):
    def get_model(self):
        raise Exception("need imp")

    def batch_load_fn(self, keys):
        model = self.get_model()
        item_list = {str(item.id): item for item in model.objects.filter(id__in=keys)}
        return Promise.resolve([item_list.get(item_id) for item_id in keys])


class UserLoader(BaseModelLoader):
    def get_model(self):
        return User


class JobLoader(BaseModelLoader):
    def get_model(self):
        return Job
