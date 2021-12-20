from aiogram import Bot, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import CallbackQuery
from aiogram.utils import executor
from sqlalchemy.exc import IntegrityError
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy.sql.elements import and_

from models import User, UserKey

import keyboard as kb
from settings import TOKEN

session_factory = sessionmaker(bind=engine)
current_session = scoped_session(session_factory)

bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)


class LoginPassword(StatesGroup):
    """Стадии создания нового логина + пароля"""
    title = State()
    login = State()
    password = State()
    end = State()
    change = State()


class ChangeKey(StatesGroup):
    start = State()
    stop = State()


@dp.message_handler(commands=('start',))
async def process_start_command(message: types.Message):
    """Отслеживание первого сообщения боту"""
    user = User(chat_id=message.from_user.id)
    current_session.add(user)
    try:
        current_session.commit()
    except IntegrityError:
        current_session.rollback()
    await message.reply("Привет!\nНапиши мне что-нибудь!", reply_markup=kb.greet_kb,)


@dp.message_handler(text='Создать пароль')
async def set_new_password(message: types.Message):
    """Создание нового ключа"""
    await LoginPassword.title.set()  # Создаем стадию получения названия
    await bot.send_message(message.from_user.id, 'Введите наименование')


@dp.message_handler(state=LoginPassword.title)
async def process_title(message: types.Message, state: FSMContext):
    """Получение названия ключа"""
    async with state.proxy() as data:
        k = current_session.query(UserKey).filter(and_(UserKey.user_id == message.from_user.id, UserKey.title == message.text))  # Проверка на существование такого названия у ключа
        exist = current_session.query(k.exists()).scalar()
        if not exist:
            data['title'] = message.text
        else:
            await bot.send_message(message.chat.id, 'Такое наименование уже есть')
            return await set_new_password(message)
    await bot.delete_message(message.chat.id, message.message_id)
    await bot.delete_message(message.chat.id, message.message_id - 1)
    await LoginPassword.next()  # Вызываем следующую стадию (логин)
    await bot.send_message(message.from_user.id, 'Введите логин')


@dp.message_handler(state=LoginPassword.login)
async def process_login(message: types.Message, state: FSMContext):
    """Получение логина"""
    async with state.proxy() as data:
        data['login'] = message.text
    await bot.delete_message(message.chat.id, message.message_id)
    await bot.delete_message(message.chat.id, message.message_id - 1)
    await LoginPassword.next()  # Вызываем следующую стадию (пароль)
    await bot.send_message(message.from_user.id, 'Введите пароль')


@dp.message_handler(state=LoginPassword.password)
async def process_password(message: types.Message, state: FSMContext, set_password=True):
    """Прием пароля и отображение state.data (Введенных ранее полей)"""
    async with state.proxy() as data:
        if set_password:
            data['password'] = message.text
        await bot.delete_message(message.chat.id, message.message_id)
        await bot.delete_message(message.chat.id, message.message_id - 1)
        reply = f'Наименование: {data["title"]}\nЛогин: {data["login"]}\nПароль: {data["password"]}'
        await bot.send_message(message.from_user.id, reply, reply_markup=kb.pre_save_kb)
    await LoginPassword.next() # Перевод на заключительную стадию (подтверждение/сохранение/отмена)


@dp.callback_query_handler(state=LoginPassword.end)
async def process_end(call: CallbackQuery, state: FSMContext):
    """Подтверждение/изменение нового пароля"""
    if call.data == 'save':
        success = True
        async with state.proxy() as data:
            key = UserKey(user_id=call.from_user.id, title=data['title'], login=data['login'], password=data['password'])
        current_session.add(key)
        try:
            current_session.commit()
        except IntegrityError:
            success = False
            current_session.rollback()
        await state.finish()
        if success:
            await bot.send_message(call.from_user.id, 'Успешно сохранено')
        else:
            await bot.send_message(call.from_user.id, 'Произошла ошибка, попробуйте снова')
    elif call.data == 'change':
        await LoginPassword.next()
        await bot.send_message(call.from_user.id, 'Что вы хотите изменить?', reply_markup=kb.pre_save_change_kb)
    elif call.data == 'cancel':
        await state.finish()
        await bot.send_message(call.from_user.id, 'Отменено')
    await bot.delete_message(call.from_user.id, call.message.message_id)


@dp.callback_query_handler(text_contains="change", state=LoginPassword.change)
async def edit_pre_save(call: CallbackQuery, state: FSMContext):
    """Редактирование перед сохранением"""
    ch = call.data.split('_')[1]
    async with state.proxy() as data:
        data[ch] = None
    await bot.delete_message(call.from_user.id, call.message.message_id)
    await bot.send_message(call.from_user.id, 'Введите новое значение')


@dp.message_handler(state=LoginPassword.change)
async def new_value_pre_save(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        for key in data:
            data[key] = message.text if not data[key] else data[key]
    await LoginPassword.password.set()
    await process_password(message, state, set_password=False)


@dp.message_handler(text='Мои пароли')
async def view_keys(message: types.Message):
    """Просмотр списка паролей"""
    keys = current_session.query(User).filter(User.chat_id == message.from_user.id).one().key
    markup = InlineKeyboardMarkup(row_width=1)
    for key in keys:
        bt = InlineKeyboardButton(text='{}: {}'.format(key.title, key.login), callback_data='key={}'.format(key.title))
        markup.insert(bt)
    await bot.delete_message(message.from_user.id, message.message_id)
    await bot.send_message(message.from_user.id, 'Сохраненные пароли', reply_markup=markup)


@dp.callback_query_handler(text_contains="key=")
async def view_key(call: CallbackQuery):
    """Отображение ключа"""
    key_title = call.data.split('=')[1]
    key = current_session.query(UserKey).filter((UserKey.user_id == call.from_user.id) & (UserKey.title == key_title)).one()
    btn = InlineKeyboardMarkup(row_width=1)
    btnCopy = InlineKeyboardButton(text='Скопировал', callback_data='copy')
    btnDelete = InlineKeyboardButton(text='Удалить', callback_data='delete_key_{}'.format(key.id))
    btnChange = InlineKeyboardButton(text='Изменить', callback_data='change_key_{}'.format(key.id))
    btn.insert(btnCopy)
    btn.insert(btnChange)
    btn.insert(btnDelete)
    await bot.delete_message(call.from_user.id, call.message.message_id)
    await bot.send_message(call.from_user.id, 'login: {}\npassword: {}'.format(key.login, key.password), reply_markup=btn)


@dp.callback_query_handler(text="copy")
async def copy_key(call: CallbackQuery):
    """Удаление сообщения с паролем после копирования"""
    await bot.delete_message(call.from_user.id, call.message.message_id)


@dp.callback_query_handler(text_contains="delete_key")
async def delete_key(call: CallbackQuery):
    """Удаление ключа"""
    key_id = call.data.split('_')[2]
    current_session.query(UserKey).filter_by(id=key_id).delete()
    current_session.commit()
    await bot.delete_message(call.from_user.id, call.message.message_id)
    await bot.send_message(call.from_user.id, 'Удалено')


@dp.callback_query_handler(text_contains="change_key")
async def delete_key(call: CallbackQuery):
    """Начало процедуры изменения ключа"""
    key_id = call.data.split('_')[2]
    btn = InlineKeyboardMarkup(row_width=1)
    btnChangeTitle = InlineKeyboardButton(text='Наименование', callback_data='change_title_{}'.format(key_id))
    btnChangeLogin = InlineKeyboardButton(text='Логин', callback_data='change_login_{}'.format(key_id))
    btnChangeKey = InlineKeyboardButton(text='Пароль', callback_data='change_password_{}'.format(key_id))
    btn.insert(btnChangeTitle)
    btn.insert(btnChangeLogin)
    btn.insert(btnChangeKey)
    await ChangeKey.start.set()
    await bot.delete_message(call.from_user.id, call.message.message_id)
    await bot.send_message(call.from_user.id, 'Что вы хотите изменить?', reply_markup=btn)


@dp.callback_query_handler(text_contains="change_", state=ChangeKey.start)
async def delete_key(call: CallbackQuery, state: FSMContext):
    value, key_id = call.data.split('_')[1:]
    async with state.proxy() as data:
        data['value'] = value
        data['id'] = int(key_id)
    await ChangeKey.next()
    await bot.delete_message(call.from_user.id, call.message.message_id)
    await bot.send_message(call.from_user.id, 'Введите новое значение')


@dp.message_handler(state=ChangeKey.stop)
async def delete_key(message: types.Message, state: FSMContext):
    success = True
    async with state.proxy() as data:
        key = current_session.query(UserKey).filter_by(id=data['id']).update({data['value']: message.text})
        try:
            current_session.commit()
        except IntegrityError:
            success = False
            current_session.rollback()
    await state.finish()
    await bot.delete_message(message.from_user.id, message.message_id)
    await bot.delete_message(message.from_user.id, message.message_id - 1)
    if success:
        await bot.send_message(message.from_user.id, 'Успешно изменено')
    else:
        await bot.send_message(message.from_user.id, 'Произошла ошибка, попробуйте снова')


if __name__ == '__main__':
    executor.start_polling(dp)
