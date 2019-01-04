import sys
import os
import logging
import json
from dbclients.tantalus import TantalusApi
from dbclients.basicclient import NotFoundError
from datamanagement.utils.runtime_args import parse_runtime_args
import pandas as pd
from sets import Set


tags_to_keep = [
    'SC-1635',
    'SC-1293',
    'SC-1294',
    'shahlab_pdx_bams_to_keep',
]


if __name__ == "__main__":
    logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.INFO)

    tantalus_api = TantalusApi()

    files_to_delete = []

    datasets_to_keep = set()

    for tag_name in tags_to_keep:
        datasets = tantalus_api.list("tag", name=tag_name)

        for dataset in datasets:
            datasets_to_keep.add(dataset["id"])

    blob_storage = tantalus_api.get_storage_client('singlecellblob')
    shahlab_storage = tantalus_api.get_storage_client('shahlab')

    all_bam_files = tantalus_api.list('sequence_dataset', dataset_type='BAM', library__library_type__name='WGS')

    total_data_size = 0
    file_num_count = 0

    for dataset in all_bam_files:
        is_on_blob = tantalus_api.is_sequence_dataset_on_storage(dataset, 'singlecellblob')
        is_on_shahlab = tantalus_api.is_sequence_dataset_on_storage(dataset, 'shahlab')

        if not is_on_shahlab:
            continue

        if not is_on_blob:
            logging.info("Dataset {} has no file instances stored in blob. Skipping...".format(dataset['name']))
            continue

        if dataset['id'] in datasets_to_keep:
            logging.info("Dataset {} is required. Skipping...".format(dataset['name']))
            continue

        file_size_check = True
        for file_instance in tantalus_api.get_sequence_dataset_file_instances(dataset, 'singlecellblob'):
            if not blob_storage.exists(file_instance['file_resource']['filename'])):
                logging.info("File {} doesnt exist on blob".format(file_instance['filepath']))
                file_size_check = False
                continue
            if blob_storage.get_size(file_instance['file_resource']['filename']) != file_instance['file_resource']['size']:
                logging.info("File {} has a different size in blob. Skipping...".format(file_instance['filepath']))
                file_size_check = False
                continue
            if not shahlab_storage.exists(file_instance['file_resource']['filename'])):
                logging.info("File {} doesnt exist on shahlab".format(file_instance['filepath']))
                file_size_check = False
                continue
            if shahlab_storage.get_size(file_instance['file_resource']['filename']) != file_instance['file_resource']['size']:
                logging.info("File {} has a different size in shahlab. Skipping...".format(file_instance['filepath']))
                file_size_check = False
                continue
            total_data_size += file_instance['file_resource']['size']
            file_num_count += 1

        if not file_size_check:
            logging.info("Dataset {} failed file size check in blob. Skipping...".format(dataset['name']))
            continue

        for file_instance in tantalus_api.get_sequence_dataset_file_instances(dataset, 'singlecellblob'):
            files_to_delete.append(shahlab_file_instance['filepath'])
            total_data_size += file_instance['file_resource']['size']
            file_num_count += 1

            #tantalus_api.delete("file_instance", file_instance['id'])

    logging.info("Total size of the {} files is {} bytes".format(
        file_num_count, total_data_size)

    with open("file_paths.txt", "w") as f:
        for path in files_to_delete:
            f.write(path +'\n')

   
