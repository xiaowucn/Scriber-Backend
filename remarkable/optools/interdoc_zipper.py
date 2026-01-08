import logging
import shutil
import zipfile
from pathlib import Path

from remarkable.common.storage import localstorage
from remarkable.config import project_root
from remarkable.db import pw_db
from remarkable.models.new_file import NewFile
from remarkable.optools.fm_upload import FMUploader


class FolderZipper:
    @staticmethod
    def zip_folder(folder_path: Path, zip_path: Path):
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for file in folder_path.rglob("*"):
                if file.is_file():
                    arcname = file.relative_to(folder_path)
                    zipf.write(file, arcname)
        logging.info("文件夹 %s 已压缩为 %s", folder_path, zip_path)

    @staticmethod
    def delete_interdoc_dir(folder_path: Path):
        shutil.rmtree(folder_path)
        logging.info("文件夹 %s 已删除", folder_path)

    @staticmethod
    def delete_zip_file(zip_path: Path):
        zip_path.unlink()
        logging.info("压缩文件 %s 已删除", zip_path)

    @staticmethod
    def upload_zip_to_fm(zip_path: Path):
        FMUploader().upload(zip_path)


class InterDocZipper(FolderZipper):
    def __init__(self, schema_id=17):
        self.schema_id = schema_id
        self.interdoc_path = Path(f"{project_root}/data/training_cache/{schema_id}/0/interdoc")
        self.training_data_path = Path(f"{project_root}/data/training_cache/{schema_id}/0/elements")

    @staticmethod
    async def interdoc_path_pair(fids):
        files = await pw_db.execute(NewFile.select(NewFile.id, NewFile.pdfinsight).where(NewFile.id.in_(fids)))
        return [(file.id, localstorage.mount(file.pdfinsight_path())) for file in files]

    def get_file_ids(self):
        return [f.name.split(".")[0] for f in self.training_data_path.iterdir() if f.is_file()]

    async def gen_zip_interdoc(self):
        fids = self.get_file_ids()
        id_path_pairs = await self.interdoc_path_pair(fids)

        self.interdoc_path.mkdir(exist_ok=True, parents=True)

        for fid, path in id_path_pairs:
            shutil.copy2(path, self.interdoc_path.joinpath(f"{fid}.interdoc.zip"))

        # zip_path = self.interdoc_path.parent.joinpath(f'{self.schema_id}-{self.interdoc_path.name}.zip')
        # self.zip_folder(self.interdoc_path, zip_path)
        # self.upload_zip_to_fm(zip_path)
        # self.delete_zip_file(zip_path)
        # self.delete_interdoc_dir(self.interdoc_path)


class TrainingDataZipper(InterDocZipper):
    def gen_zip_training_data(self):
        zip_path = self.training_data_path.parent.joinpath(f"{self.schema_id}-{self.training_data_path.name}.zip")
        self.zip_folder(self.training_data_path, zip_path)


if __name__ == "__main__":
    import asyncio

    zipper = InterDocZipper(schema_id=3)
    asyncio.run(zipper.gen_zip_interdoc())
