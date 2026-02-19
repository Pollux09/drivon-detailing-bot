from aiogram.fsm.state import State, StatesGroup


class BookingStates(StatesGroup):
    choosing_service = State()
    choosing_car_type = State()
    choosing_date = State()
    choosing_time = State()
    confirming = State()


class AdminServiceCreateStates(StatesGroup):
    waiting_name = State()
    waiting_description = State()
    waiting_duration = State()
    waiting_price = State()


class AdminServiceEditStates(StatesGroup):
    waiting_value = State()


class AdminCarCreateStates(StatesGroup):
    waiting_name = State()
    waiting_multiplier = State()


class AdminCarEditStates(StatesGroup):
    waiting_value = State()


class AdminCloseSlotStates(StatesGroup):
    waiting_date = State()
    waiting_start_hour = State()
    waiting_duration = State()


class AdminMoveBookingStates(StatesGroup):
    waiting_date = State()
    waiting_time = State()


class AdminBookingNoteStates(StatesGroup):
    waiting_text = State()


class AdminCancelBookingStates(StatesGroup):
    waiting_reason = State()
