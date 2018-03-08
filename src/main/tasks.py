# -*- coding: UTF-8 -*-
# tasks.py
# Noah Rubin
# 02/05/2018

import logging
Logger = logging.getLogger(__name__)
from os import path
from hashlib import md5
from itertools import chain as itertools_chain
from datetime import datetime, timezone, timedelta
from json import dumps
from construct import Container

from src.parsers.mft import MFTEntry

class ParseCSVTask(object):
    '''
    '''
    NULL = ''

    def __init__(self, nodeidx, recordidx, info_type, mft_record, target=None, sep=None):
        self.nodeidx = nodeidx
        self.recordidx = recordidx
        self.info_type = info_type
        self.mft_record = mft_record
        self.target = target
        self.sep = sep
    def __call__(self, worker_name):
        mft_entry = MFTEntry(self.mft_record)
        target_file = self.target
        #target_file = path.join(self.target, '%s_amft_csv.tmp'%worker_name)
        result_set = list()
        if self.info_type == 'summary':
            # FIELDS: RecordNumber, Signature, SequenceNumber, LogFileSequenceNumber, BaseFileRecordSegmentNumber, BaseFileRecordSequenceNumber, 
            #         Active, HasIndex, UsedSize, TotalSize, ReferenceCount, FirstAttributeId, FileName,
            #         StandardInformationModifyDate, StandardInformationAccessDate, StandardInformationCreateDate, StandardInformationEntryDate,
            #         FileNameModifyDate, FileNameAccessDate, FileNameCreateDate, FileNameEntryDate,
            #         StandardInformationCount, AttributeListCount, FileNameCount, ObjectIDCount, SecurityDescriptorCount, VolumeNameCount,
            #         VolumeInformationCount, DataCount, IndexRootCount, IndexAllocationCount
            try:
                mft_entry.parse()
            except Exception as e:
                raise
                Logger.error('Failed to parse MFT entry %d for node %d (%s)'%(self.recordidx, self.nodeidx, str(e)))
            else:
                result = list()
                result.append(str(self.nodeidx))
                result.append(str(self.recordidx))
                result.append(str(mft_entry.Header.MFTRecordNumber))
                result.append(str(mft_entry.Header.MultiSectorHeader.Signature))
                result.append(str(mft_entry.Header.SequenceNumber))
                result.append(str(mft_entry.Header.LogFileSequenceNumber))
                result.append(str(mft_entry.Header.BaseFileRecordSegment.SegmentNumber))
                result.append(str(mft_entry.Header.BaseFileRecordSegment.SequenceNumber))
                result.append(str(mft_entry.Header.Flags.ACTIVE))
                result.append(str(mft_entry.Header.Flags.HAS_INDEX))
                result.append(str(mft_entry.Header.UsedSize))
                result.append(str(mft_entry.Header.TotalSize))
                result.append(str(mft_entry.Header.ReferenceCount))
                result.append(str(mft_entry.Header.FirstAttributeId))
                result.append(str(mft_entry.Attributes.FILE_NAME[0].Data.FileName if len(mft_entry.Attributes.FILE_NAME) > 0 else self.NULL))
                if len(mft_entry.Attributes.STANDARD_INFORMATION) > 0:
                    result.append(mft_entry.Attributes.STANDARD_INFORMATION[0].Data.LastModifiedTime.strftime('%Y-%m-%d %H:%M:%S.%f%z'))
                    result.append(mft_entry.Attributes.STANDARD_INFORMATION[0].Data.LastAccessTime.strftime('%Y-%m-%d %H:%M:%S.%f%z'))
                    result.append(mft_entry.Attributes.STANDARD_INFORMATION[0].Data.CreateTime.strftime('%Y-%m-%d %H:%M:%S.%f%z'))
                    result.append(mft_entry.Attributes.STANDARD_INFORMATION[0].Data.EntryModifiedTime.strftime('%Y-%m-%d %H:%M:%S.%f%z'))
                else:
                    result.append(self.NULL)
                    result.append(self.NULL)
                    result.append(self.NULL)
                    result.append(self.NULL)
                if len(mft_entry.Attributes.FILE_NAME) > 0:
                    result.append(mft_entry.Attributes.FILE_NAME[0].Data.LastModifiedTime.strftime('%Y-%m-%d %H:%M:%S.%f%z'))
                    result.append(mft_entry.Attributes.FILE_NAME[0].Data.LastAccessTime.strftime('%Y-%m-%d %H:%M:%S.%f%z'))
                    result.append(mft_entry.Attributes.FILE_NAME[0].Data.CreateTime.strftime('%Y-%m-%d %H:%M:%S.%f%z'))
                    result.append(mft_entry.Attributes.FILE_NAME[0].Data.EntryModifiedTime.strftime('%Y-%m-%d %H:%M:%S.%f%z'))
                else:
                    result.append(self.NULL)
                    result.append(self.NULL)
                    result.append(self.NULL)
                    result.append(self.NULL)
                for key in mft_entry.Attributes.iterkeys:
                    result.append(str(len(mft_entry.Attributes[key])))
                result_set.append(result)
        try:
            if len(result_set) > 0:
                with open(target_file, 'a') as f:
                    for result in result_set:
                        f.write(self.sep.join(result) + '\n')
        except Exception as e:
            Logger.error('Failed to write results to output file %s (%s)'%(target_file, str(e)))

class ParseBODYTask(object):
    '''
    '''
    NULL = ''
    
    @staticmethod
    def to_timestamp(dt):
        '''
        Args:
            dt: DateTime<UTC>   => datetime object to convert
        Returns:
            Datetime object converted to Unix epoch time
        Preconditions:
            dt is timezone-aware timestamp with timezone UTC
        '''
        return (dt - datetime(1970,1,1, tzinfo=timezone.utc)) / timedelta(seconds=1)

    def __init__(self, nodeidx, recordidx, mft_record, target=None, sep=None):
        self.nodeidx = nodeidx
        self.recordidx = recordidx
        self.mft_record = mft_record
        self.target = target
        self.sep = sep
    def __call__(self, worker_name):
        mft_entry = MFTEntry(self.mft_record)
        target_file = self.target
        #target_file = path.join(self.target, '%s_amft_csv.tmp'%worker_name)
        result_set = list()
        # FIELDS: MD5|name|inode|mode_as_string|UID|GID|size|atime|mtime|ctime|crtime
        try:
            mft_entry.parse()
        except Exception as e:
            Logger.error('Failed to parse MFT entry %d for node %d (%s)'%(self.recordidx, self.nodeidx, str(e)))
        else:
            if len(mft_entry.Attributes.STANDARD_INFORMATION) > 0 or len(mft_entry.Attributes.FILE_NAME) > 0:
                file_name = str(mft_entry.Attributes.FILE_NAME[0].Data.FileName if len(mft_entry.Attributes.FILE_NAME) > 0 else self.NULL)
                file_size = str(mft_entry.Attributes.FILE_NAME[0].Data.FileSize if len(mft_entry.Attributes.FILE_NAME) > 0 else self.NULL)
                md5hash = md5(self.mft_record).hexdigest()
                for attribute in itertools_chain(mft_entry.Attributes.STANDARD_INFORMATION, mft_entry.Attributes.FILE_NAME):
                    result = list()
                    result.append(str(self.nodeidx))
                    result.append(str(self.recordidx))
                    result.append(md5hash)
                    result.append(file_name)
                    result.append(self.NULL)
                    result.append(self.NULL)
                    result.append(self.NULL)
                    result.append(self.NULL)
                    result.append(str(file_size))
                    result.append(str(self.to_timestamp(attribute.Data.LastAccessTime)))
                    result.append(str(self.to_timestamp(attribute.Data.LastModifiedTime)))
                    result.append(str(self.to_timestamp(attribute.Data.EntryModifiedTime)))
                    result.append(str(self.to_timestamp(attribute.Data.CreateTime)))
                    result_set.append(result)
        try:
            if len(result_set) > 0:
                with open(target_file, 'a') as f:
                    for result in result_set:
                        try:
                            f.write(self.sep.join(result) + '\n')
                        except Exception as e:
                            Logger.error('Failed to write result to output file %s (%s)'%(target_file, str(e)))
        except Exception as e:
            Logger.error('Failed to write results to output file %s (%s)'%(target_file, str(e)))

class ParseJSONTask(object):
    '''
    '''
    NULL = ''
    
    def __init__(self, nodeidx, recordidx, mft_record, target=None, pretty=None):
        self.nodeidx = nodeidx
        self.recordidx = recordidx
        self.mft_record = mft_record
        self.target = target
        self.pretty = pretty
    def __call__(self, worker_name):
        mft_entry = MFTEntry(self.mft_record)
        target_file = self.target
        #target_file = path.join(self.target, '%s_amft_csv.tmp'%worker_name)
        result_set = list()
        try:
            mft_entry.parse()
            ## This is lazy - figure out why FieldBountDict is not serializable
            ## It appears that FieldBoundDict needs to implement __dict__
            for attribute in itertools_chain(mft_entry.Attributes.STANDARD_INFORMATION, mft_entry.Attributes.FILE_NAME):
                attribute.Data.LastAccessTime = attribute.Data.LastAccessTime.strftime('%Y-%m-%d %H:%M:%S.%f%z')
                attribute.Data.LastModifiedTime = attribute.Data.LastModifiedTime.strftime('%Y-%m-%d %H:%M:%S.%f%z')
                attribute.Data.EntryModifiedTime = attribute.Data.EntryModifiedTime.strftime('%Y-%m-%d %H:%M:%S.%f%z')
                attribute.Data.CreateTime = attribute.Data.CreateTime.strftime('%Y-%m-%d %H:%M:%S.%f%z')
            for attribute_list in mft_entry.Attributes.ATTRIBUTE_LIST:
                attribute_list = Container(**attribute_list)
            for attribute_type in mft_entry.Attributes.iterkeys:
                if len(mft_entry.Attributes[attribute_type]) == 0:
                    mft_entry.Attributes[attribute_type] = None
            serializable_entry = Container(**mft_entry)
            serializable_entry.Attributes = Container(**serializable_entry.Attributes)
            serializable_entry.nodeidx = self.nodeidx
            serializable_entry.recordidx = self.recordidx
            result = dumps(serializable_entry, sort_keys=True, indent=(2 if self.pretty else None))
        except Exception as e:
            Logger.error('Failed to parse MFT entry %d for node %d (%s)'%(self.recordidx, self.nodeidx, str(e)))
        else:
            result_set.append(result)
        try:
            if len(result_set) > 0:
                with open(target_file, 'a') as f:
                    for result in result_set:
                        try:
                            f.write(result + '\n')
                        except Exception as e:
                            Logger.error('Failed to write result to output file %s (%s)'%(target_file, str(e)))
        except Exception as e:
            Logger.error('Failed to write results to output file %s (%s)'%(target_file, str(e)))
