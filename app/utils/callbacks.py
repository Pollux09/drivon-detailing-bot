from __future__ import annotations

from aiogram.filters.callback_data import CallbackData


class MenuActionCb(CallbackData, prefix="menu"):
    action: str


class ServiceSelectCb(CallbackData, prefix="svc"):
    service_id: int


class CarTypeSelectCb(CallbackData, prefix="car"):
    car_type_id: int


class DateSelectCb(CallbackData, prefix="date"):
    day: str


class TimeSelectCb(CallbackData, prefix="time"):
    ts: int


class ConfirmCb(CallbackData, prefix="confirm"):
    action: str


class AdminActionCb(CallbackData, prefix="admin"):
    action: str


class AdminServiceCb(CallbackData, prefix="admin_svc"):
    service_id: int
    action: str


class AdminCarCb(CallbackData, prefix="admin_car"):
    car_type_id: int
    action: str


class AdminBookingCb(CallbackData, prefix="admin_bk"):
    booking_id: int
    action: str


class AdminBlockCb(CallbackData, prefix="admin_blk"):
    block_id: int
    action: str
