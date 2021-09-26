from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup

btnSetPassword = KeyboardButton('Создать пароль')
btnViewKeys = KeyboardButton('Мои пароли')
greet_kb = ReplyKeyboardMarkup()
greet_kb.insert(btnSetPassword)
greet_kb.insert(btnViewKeys)

btnChange = InlineKeyboardButton(text='Редактировать', callback_data='change')
btnSave = InlineKeyboardButton(text='Сохранить', callback_data='save')
btnCancel = InlineKeyboardButton(text='Отменить', callback_data='cancel')
pre_save_kb = InlineKeyboardMarkup(row_width=1)
pre_save_kb.insert(btnChange)
pre_save_kb.insert(btnSave)
pre_save_kb.insert(btnCancel)

btnChangeTitle = InlineKeyboardButton(text='Наименование', callback_data='change_title')
btnChangeLogin = InlineKeyboardButton(text='Логин', callback_data='change_login')
btnChangePassword = InlineKeyboardButton(text='Пароль', callback_data='change_password')
pre_save_change_kb = InlineKeyboardMarkup(row_width=1)
pre_save_change_kb.insert(btnChangeTitle)
pre_save_change_kb.insert(btnChangeLogin)
pre_save_change_kb.insert(btnChangePassword)
