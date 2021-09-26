from aiogram import Bot, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import CallbackQuery
from aiogram.utils import executor
from sqlalchemy.exc import IntegrityError
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from main.models import *

import keyboard as kb
from settings import TOKEN

session_factory = sessionmaker(bind=engine)
current_session = scoped_session(session_factory)

bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)


class LoginPassword(StatesGroup):
    title = State()
    login = State()
    password = State()
    end = State()


@dp.message_handler(commands=('start',))
async def process_start_command(message: types.Message):
    user = User(chat_id=message.from_user.id)
    current_session.add(user)
    try:
        current_session.commit()
    except IntegrityError:
        current_session.rollback()
    await message.reply("Привет!\nНапиши мне что-нибудь!", reply_markup=kb.greet_kb,)


@dp.message_handler(commands=('help',))
async def process_help_command(message: types.Message):
    await message.reply("Напиши мне что-нибудь, и я отпрпавлю этот текст тебе в ответ!")


@dp.message_handler(text='Создать пароль')
async def set_new_password(message: types.Message):
    await LoginPassword.title.set()
    await bot.send_message(message.from_user.id, 'Введите наименование')


@dp.message_handler(state=LoginPassword.title)
async def process_title(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['title'] = message.text
    await LoginPassword.next()
    await bot.send_message(message.from_user.id, 'Введите логин')


@dp.message_handler(state=LoginPassword.login)
async def process_login(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['login'] = message.text
    await LoginPassword.next()
    await bot.send_message(message.from_user.id, 'Введите пароль')


@dp.message_handler(state=LoginPassword.password)
async def process_password(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['password'] = message.text
        reply = f'Наименование: {data["title"]}\nЛогин: {data["login"]}\nПароль: {data["password"]}'
        await bot.send_message(message.from_user.id, reply, reply_markup=kb.pre_save_kb)
    await LoginPassword.next()


@dp.callback_query_handler(state=LoginPassword.end)
async def process_end(call: CallbackQuery, state: FSMContext):
    print(call.data)
    if call.data == 'save':
        async with state.proxy() as data:
            key = UserKey(user_id=call.from_user.id, title=data['title'], login=data['login'], password=data['password'])
        current_session.add(key)
        current_session.commit()
        await state.finish()
        await bot.send_message(call.from_user.id, 'Успешно сохранено')
    elif call.data == 'change':
        await LoginPassword.first()
        await bot.send_message(call.from_user.id, 'Введите наименование')
    elif call.data == 'cancel':
        await state.finish()
        await bot.send_message(call.from_user.id, 'Отменено')


@dp.message_handler(text='Мои пароли')
async def view_keys(message: types.Message):
    keys = current_session.query(User).filter(User.chat_id == message.from_user.id).one().key
    markup = InlineKeyboardMarkup(row_width=1)
    for key in keys:
        bt = InlineKeyboardButton(text='{}: {}'.format(key.title, key.login), callback_data='key={}'.format(key.title))
        markup.insert(bt)
    await bot.send_message(message.from_user.id, 'Сохраненные пароли', reply_markup=markup)


@dp.callback_query_handler(text_contains="key")
async def view_key(call: CallbackQuery):
    key_title = call.data.split('=')[1]
    print(f'key_title={key_title}')
    key = current_session.query(UserKey).filter((UserKey.user_id == call.from_user.id) & (UserKey.title == key_title)).one()
    await bot.send_message(call.from_user.id, 'login: {}\npassword: {}'.format(key.login, key.password))

if __name__ == '__main__':
    executor.start_polling(dp)