# coding=utf-8
# Created by 0xFranCiS on May 28, 2016.


class BusinessException(Exception):
    pass


class EntityNotFound(BusinessException):
    pass


class SecurityException(BusinessException):
    pass


class HttpException(Exception):
    pass


class DatabaseException(Exception):
    pass

