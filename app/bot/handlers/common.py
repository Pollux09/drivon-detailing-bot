from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.filters import IsAdminFilter
from app.bot.handlers.helpers import edit_or_answer
from app.bot.keyboards.admin import admin_menu_keyboard
from app.bot.keyboards.user import main_menu_keyboard
from app.config import Settings
from app.services.user_service import get_or_create_user
from app.utils.callbacks import AdminActionCb, MenuActionCb


router = Router(name="common")


@router.message(CommandStart())
async def start_handler(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
) -> None:
    await state.clear()

    if message.from_user is None:
        return

    user = await get_or_create_user(
        session=session,
        telegram_id=message.from_user.id,
        full_name=message.from_user.full_name,
        is_admin=message.from_user.id in settings.admin_ids,
    )

    greeting = "Добро пожаловать. Выберите действие:"
    if user.role.value == "admin":
        await message.answer("Админ-панель", reply_markup=admin_menu_keyboard())
        return

    await message.answer(greeting, reply_markup=main_menu_keyboard())


@router.message(Command("admin"), IsAdminFilter())
async def admin_command_handler(message: Message) -> None:
    await message.answer("Админ-панель", reply_markup=admin_menu_keyboard())


@router.callback_query(MenuActionCb.filter(F.action == "main"))
async def to_main_menu(query: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await edit_or_answer(query, "Главное меню", reply_markup=main_menu_keyboard())
    await query.answer()


@router.callback_query(MenuActionCb.filter(F.action == "price"))
async def show_price(
    query: CallbackQuery,
    booking_service,
    session: AsyncSession,
) -> None:
    services = await booking_service.get_active_services(session)
    if not services:
        text = "Прайс пока пуст."
    else:
        lines = ["💰 Прайс:"]
        for service in services:
            lines.append(f"• {service.name} — от {service.base_price} ₽")
        text = "\n".join(lines)

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⬅️ В меню", callback_data=MenuActionCb(action="main").pack()))
    await edit_or_answer(query, text, builder.as_markup())
    await query.answer()


@router.callback_query(MenuActionCb.filter(F.action == "works"))
async def show_works(query: CallbackQuery, settings: Settings) -> None:
    builder = InlineKeyboardBuilder()
    if settings.works_url:
        builder.row(InlineKeyboardButton(text="Открыть", url=settings.works_url))
    builder.row(InlineKeyboardButton(text="⬅️ В меню", callback_data=MenuActionCb(action="main").pack()))
    await edit_or_answer(query, "📸 Наши работы", builder.as_markup())
    await query.answer()


@router.callback_query(MenuActionCb.filter(F.action == "promotions"))
async def show_promotions(query: CallbackQuery, settings: Settings) -> None:
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⬅️ В меню", callback_data=MenuActionCb(action="main").pack())]]
    )
    await edit_or_answer(query, f"🎁 {settings.promotions_text}", keyboard)
    await query.answer()


@router.callback_query(MenuActionCb.filter(F.action == "contacts"))
async def show_contacts(query: CallbackQuery, settings: Settings) -> None:
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⬅️ В меню", callback_data=MenuActionCb(action="main").pack())]]
    )
    await edit_or_answer(query, settings.contacts_text, keyboard)
    await query.answer()


@router.callback_query(MenuActionCb.filter(F.action == "contact_admin"))
async def show_admin_contact(query: CallbackQuery, settings: Settings) -> None:
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⬅️ В меню", callback_data=MenuActionCb(action="main").pack())]]
    )
    await edit_or_answer(query, f"👨‍💼 {settings.admin_contact}", keyboard)
    await query.answer()


@router.callback_query(AdminActionCb.filter(F.action == "menu"), IsAdminFilter())
async def back_to_admin_menu(query: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await edit_or_answer(query, "Админ-панель", reply_markup=admin_menu_keyboard())
    await query.answer()
