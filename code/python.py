from android.view import Gravity, View
from android.widget import FrameLayout, LinearLayout, ScrollView, TextView
from android.graphics.drawable import GradientDrawable
from android.content.res import ColorStateList
from android.graphics import Color, Typeface
from android.util import TypedValue
from android.text import SpannableStringBuilder, Spanned
from android.text.style import ForegroundColorSpan, AbsoluteSizeSpan

from org.telegram.messenger import AndroidUtilities, R as R_tg, LocaleController, BuildVars
from org.telegram.ui.ActionBar import Theme
from org.telegram.ui.Components import EditTextBoldCursor, LayoutHelper

from java.lang import Class as JClass
from java import jarray, jint

from base_plugin import BasePlugin, MenuItemData, MenuItemType, MethodHook
from android_utils import run_on_ui_thread, OnClickListener, log
from client_utils import send_text, edit_message, get_messages_controller
from ui.settings import Header, Text, Divider, Input, Selector
from ui.alert import AlertDialogBuilder
from ui.bulletin import BulletinHelper
from typing import Any, List, Dict

__id__ = "todo_list"
__name__ = "Todo List"
__description__ = "[eng] Interactive task lists in chat. Create: attachment menu → Todo List. Toggle: tap task in card. Edit: tap Edit button or long-press message → Todo List. Customize done/pending markers in settings.\n[ru] Интерактивные списки задач в чате. Создать: три точки в чате → Todo List. Отметить: нажать на задачу в карточке. Редактировать: кнопка Edit или зажать сообщение → Todo List. Маркеры настраиваются в настройках."
__author__ = "@itNotMax - @MaxExteraPlugins"
__version__ = "1.4.0"
__icon__ = "MaxExteraPluginsStickers/21"
__min_version__ = "12.10.6"
__app_version__ = ">=12.5.1"
__sdk_version__ = ">=1.4.3.3"

MATCH_PARENT = -1
WRAP_CONTENT = -2
SPAN_EXCL = Spanned.SPAN_EXCLUSIVE_EXCLUSIVE

TODO_PREFIX = "\U0001f4cb"
DEFAULT_DONE = "✅"
DEFAULT_PENDING = "⏳"
TODO_SEP = "━" * 14
MAX_TASKS = 28
MAX_TITLE_LEN = 128
MAX_TASK_LEN = 256
CARD_TAG_PREFIX = "exteraTodoCard|"
HEIGHT_TAG_PREFIX = "todoH_"

_plugin_ref = None
_msg_data_cache = {}
_card_heights = {}
_cell_height_state = {}

_CLR_WHITE = Color.parseColor("#FFFFFF")
_CLR_BLACK = Color.parseColor("#000000")
_CLR_GRAY = Color.parseColor("#999999")
_CLR_BLUE = Color.parseColor("#2196F3")
_CLR_DIVIDER_LIGHT = Color.parseColor("#DDDDDD")
_CLR_DIVIDER_DARK = Color.parseColor("#333333")

_EMPTY_STATES = jarray(jarray(jint))([[]])

_STRINGS = {
    "header_loc": {
        "en": "Localization",
        "ru": "Локализация",
    },
    "lang_select": {
        "en": "Language",
        "ru": "Язык",
    },
    "header_info": {
        "en": "Information",
        "ru": "Информация",
    },
    "info_channel": {
        "en": "Channel",
        "ru": "Канал",
    },
    "info_doc": {
        "en": "Documentation",
        "ru": "Документация",
    },
    "header_custom": {
        "en": "Customization",
        "ru": "Кастомизация",
    },
    "done_emoji_title": {
        "en": "Done emoji",
        "ru": "Эмодзи выполнено",
    },
    "done_emoji_sub": {
        "en": "Emoji for completed tasks (default: {def_emoji})",
        "ru": "Эмодзи для выполненных задач (по умолчанию: {def_emoji})",
    },
    "pending_emoji_title": {
        "en": "Pending emoji",
        "ru": "Эмодзи в ожидании",
    },
    "pending_emoji_sub": {
        "en": "Symbol for pending tasks (default: {def_emoji})",
        "ru": "Символ для ожидающих задач (по умолчанию: {def_emoji})",
    },
    "menu_todo_list": {
        "en": "Todo List",
        "ru": "Список задач",
    },
    "completed_count": {
        "en": "{done}/{total} completed",
        "ru": "{done}/{total} выполнено",
    },
    "edit_btn": {
        "en": "Edit",
        "ru": "Изменить",
    },
    "only_author_toggle": {
        "en": "Only author can toggle tasks",
        "ru": "Только автор может отмечать задачи",
    },
    "only_author_edit": {
        "en": "Can only edit your own lists",
        "ru": "Редактировать можно только свои списки",
    },
    "save_btn": {
        "en": "Save",
        "ru": "Сохранить",
    },
    "edit_neutral_btn": {
        "en": "✏️ Edit",
        "ru": "✏️ Изменить",
    },
    "edit_todo_title": {
        "en": "✏️ Edit Todo",
        "ru": "✏️ Редактирование списка",
    },
    "list_title_hint": {
        "en": "List title",
        "ru": "Название списка",
    },
    "subtitle_hint": {
        "en": "Subtitle (optional)",
        "ru": "Подзаголовок (необязательно)",
    },
    "max_tasks_err": {
        "en": "Maximum {max} tasks",
        "ru": "Максимум {max} задач",
    },
    "task_hint": {
        "en": "Task {num}",
        "ru": "Задача {num}",
    },
    "add_task_btn": {
        "en": "＋ Add task",
        "ru": "＋ Добавить задачу",
    },
    "enter_title_err": {
        "en": "Enter a title",
        "ru": "Введите название",
    },
    "new_todo_title": {
        "en": "New Todo List",
        "ru": "Новый список задач",
    },
    "title_long_err": {
        "en": "Title too long",
        "ru": "Название слишком длинное",
    },
    "add_one_task_err": {
        "en": "Add at least one task",
        "ru": "Добавьте хотя бы одну задачу",
    },
    "send_btn": {
        "en": "Send",
        "ru": "Отправить",
    },
}


def _app_version():
    try:
        return str(BuildVars.BUILD_VERSION_STRING).strip()
    except Exception:
        return ""


def _render_disabled():
    v = _app_version()
    if not v:
        return False
    parts = v.split(".")
    try:
        nums = tuple(int(x) for x in parts[:3])
    except Exception:
        return v.startswith("12.5.1")
    return nums == (12, 5, 1)


def _get_lang(plugin=None):
    ref = plugin or _plugin_ref
    if ref:
        try:
            val = ref.get_setting("lang", 0)
            if val == 1 or str(val) == "1" or str(val).lower() in ("ru", "русский"):
                return "ru"
        except Exception:
            pass
    return "en"


def _L(key, plugin=None, **kwargs):
    lang = _get_lang(plugin)
    st = _STRINGS.get(key, {})
    res = st.get(lang, st.get("en", key))
    if kwargs:
        try:
            return res.format(**kwargs)
        except Exception:
            return res
    return res


def _make_csl(color):
    return ColorStateList(_EMPTY_STATES, jarray(jint)([color]))


def _is_dark():
    try:
        return Theme.isCurrentThemeDark()
    except Exception:
        return False


def _csl(key):
    try:
        return _make_csl(Theme.getColor(key))
    except Exception:
        if _is_dark():
            return _make_csl(_CLR_WHITE)
        return _make_csl(_CLR_BLACK)


def _fg():
    return _csl(Theme.key_dialogTextBlack)


def _fg_hint():
    try:
        c = Theme.getColor(Theme.key_dialogTextHint)
        if c is not None and c != 0:
            return _make_csl(c)
        c = Theme.getColor(Theme.key_dialogTextGray2)
        if c is not None and c != 0:
            return _make_csl(c)
    except Exception:
        pass
    return _make_csl(_CLR_GRAY)


def _fg_blue():
    return _csl(Theme.key_dialogTextBlue2)


def _safe_set_hint_color(view, csl):
    try:
        view.setHintTextColor(csl)
    except Exception:
        pass


def _divider():
    return _CLR_DIVIDER_DARK if _is_dark() else _CLR_DIVIDER_LIGHT


def _done_emoji():
    if _plugin_ref:
        v = _plugin_ref.get_setting("emoji_done", DEFAULT_DONE)
        if v:
            return v
    return DEFAULT_DONE


def _pending_emoji():
    if _plugin_ref:
        v = _plugin_ref.get_setting("emoji_pending", DEFAULT_PENDING)
        if v:
            return v
    return DEFAULT_PENDING


def _u16len(s):
    return len(s.encode("utf-16-le")) // 2


def _esc(t):
    return str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_html(title, subtitle, tasks, done=None):
    if done is None:
        done = []
    de = _done_emoji()
    pe = _pending_emoji()
    p = ["<b>" + TODO_PREFIX + " " + _esc(title) + "</b>"]
    if subtitle:
        p.append("<i>" + _esc(subtitle) + "</i>")
    p.append(TODO_SEP)
    for i, t in enumerate(tasks):
        tid = i + 1
        tx = _esc(t)
        if tid in done:
            p.append("[" + de + "] <s>" + tx + "</s>")
        else:
            p.append("[" + pe + "] " + tx)
    return "\n".join(p)


def _strip_s_tags(text):
    s = text.strip()
    if s.startswith("<s>") and s.endswith("</s>"):
        return s[3:-4], True
    return s, False


def _parse_bracketed_marker(line):
    s = line.strip()
    if not s.startswith("["):
        return None, s
    close = s.find("]")
    if close == -1:
        return None, s
    marker = s[1:close]
    rest = s[close + 1:].strip()
    return marker, rest


def parse_todo(text):
    if not text or not isinstance(text, str):
        return None
    ls = text.strip().split("\n")
    if len(ls) < 3:
        return None
    if not ls[0].startswith(TODO_PREFIX):
        return None
    title = ls[0][len(TODO_PREFIX):].strip()
    sub = ""
    ts = -1
    if ls[1] == TODO_SEP:
        ts = 2
    elif len(ls) >= 4 and ls[2] == TODO_SEP:
        sub = ls[1]
        ts = 3
    else:
        return None
    if ts >= len(ls):
        return None
    de = _done_emoji()
    pe = _pending_emoji()
    known_done = {de, DEFAULT_DONE, "✅"}
    known_pending = {pe, DEFAULT_PENDING, "⏳", "⠀", "🔄"}
    tasks = []
    done = []
    for i, l in enumerate(ls[ts:]):
        tid = i + 1
        stripped = l.strip()
        if not stripped:
            continue
        marker, rest = _parse_bracketed_marker(stripped)
        if marker is not None:
            clean_task, had_s = _strip_s_tags(rest)
            if had_s or marker in known_done:
                done.append(tid)
            tasks.append(clean_task)
            continue
        matched = False
        for d in sorted(known_done, key=len, reverse=True):
            if stripped.startswith(d):
                raw_task = stripped[len(d):].strip()
                clean_task, had_s = _strip_s_tags(raw_task)
                done.append(tid)
                tasks.append(clean_task)
                matched = True
                break
        if not matched:
            for pend in sorted(known_pending, key=len, reverse=True):
                if stripped.startswith(pend):
                    tasks.append(stripped[len(pend):].strip())
                    matched = True
                    break
        if not matched:
            clean_task, had_s = _strip_s_tags(stripped)
            if had_s:
                done.append(tid)
            tasks.append(clean_task)
    if not tasks:
        return None
    return {"title": title, "sub": sub, "tasks": tasks, "done": done}


def _get_msg_key(mo):
    try:
        mid = mo.getId()
        did = mo.getDialogId()
        return (did, mid)
    except Exception:
        return None


def _make_card_tag(key, raw):
    return CARD_TAG_PREFIX + str(key[0]) + ":" + str(key[1]) + ":" + str(hash(raw))


def _find_card(cell):
    try:
        for i in range(cell.getChildCount()):
            child = cell.getChildAt(i)
            if child is not None:
                try:
                    tag = child.getTag()
                    if tag is not None and str(tag).startswith(CARD_TAG_PREFIX):
                        return child
                except Exception:
                    pass
    except Exception:
        pass
    return None


def _find_card_tag(cell):
    try:
        for i in range(cell.getChildCount()):
            child = cell.getChildAt(i)
            if child is not None:
                try:
                    tag = child.getTag()
                    if tag is not None and str(tag).startswith(CARD_TAG_PREFIX):
                        return str(tag)
                except Exception:
                    pass
    except Exception:
        pass
    return None


def _remove_card(cell):
    try:
        try:
            cid = cell.hashCode()
        except Exception:
            cid = id(cell)
        _cell_height_state.pop(cid, None)
    except Exception:
        pass
    try:
        for i in range(cell.getChildCount() - 1, -1, -1):
            child = cell.getChildAt(i)
            if child is not None:
                try:
                    tag = child.getTag()
                    if tag is not None and str(tag).startswith(CARD_TAG_PREFIX):
                        cell.removeViewAt(i)
                except Exception:
                    pass
    except Exception:
        pass


def _get_mo_from_cell(cell):
    try:
        if hasattr(cell, "getMessageObject"):
            mo = cell.getMessageObject()
            if mo is not None:
                return mo
    except Exception:
        pass
    try:
        mo = cell.JA.currentMessageObject
        if mo is not None:
            return mo
    except Exception:
        pass
    try:
        from hook_utils import get_field
        mo = get_field(cell, "currentMessageObject")
        if mo is not None:
            return mo
    except Exception:
        pass
    return None


def _build_card(ctx, parsed, mo, key, card_tag):
    dp = AndroidUtilities.dp
    is_out = mo.isOut()
    text_color = _csl(Theme.key_chat_messageTextOut if is_out else Theme.key_chat_messageTextIn)
    link_color = _csl(Theme.key_chat_messageLinkOut if is_out else Theme.key_chat_messageLinkIn)
    divider_color = _divider()

    card = LinearLayout(ctx)
    card.setOrientation(LinearLayout.VERTICAL)
    card.setTag(card_tag)
    card.setPadding(dp(4), 0, dp(8), 0)

    title_tv = TextView(ctx)
    title_tv.setText(parsed["title"])
    title_tv.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 15)
    title_tv.setTypeface(Typeface.DEFAULT_BOLD)
    title_tv.setTextColor(text_color)
    card.addView(title_tv, LayoutHelper.createLinear(MATCH_PARENT, WRAP_CONTENT, 0, 0, 0, 2))

    if parsed["sub"]:
        sub_tv = TextView(ctx)
        sub_tv.setText(parsed["sub"])
        sub_tv.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 13)
        sub_tv.setTypeface(None, Typeface.ITALIC)
        sub_tv.setTextColor(text_color)
        card.addView(sub_tv, LayoutHelper.createLinear(MATCH_PARENT, WRAP_CONTENT, 0, 0, 0, 2))

    sep1 = View(ctx)
    sep1.setBackgroundColor(divider_color)
    card.addView(sep1, LayoutHelper.createLinear(MATCH_PARENT, 1, 0, 6, 0, 4))

    done_set = set(parsed["done"])
    for i, task in enumerate(parsed["tasks"]):
        tid = i + 1
        is_done = tid in done_set

        row = LinearLayout(ctx)
        row.setOrientation(LinearLayout.HORIZONTAL)
        row.setGravity(Gravity.CENTER_VERTICAL)
        row.setPadding(0, dp(5), 0, dp(5))

        cs = dp(20)
        clp = LinearLayout.LayoutParams(cs, cs)
        clp.setMargins(0, 0, dp(12), 0)

        if is_done:
            frame = FrameLayout(ctx)
            frame.setLayoutParams(clp)
            cview = View(ctx)
            cbg = GradientDrawable()
            cbg.setShape(GradientDrawable.OVAL)
            cbg.setColor(link_color)
            cview.setBackground(cbg)
            frame.addView(cview, FrameLayout.LayoutParams(MATCH_PARENT, MATCH_PARENT))
            chk = TextView(ctx)
            chk.setText("✓")
            chk.setTextColor(_make_csl(_CLR_WHITE))
            chk.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 12)
            chk.setGravity(Gravity.CENTER)
            frame.addView(chk, FrameLayout.LayoutParams(MATCH_PARENT, MATCH_PARENT))
            row.addView(frame)
        else:
            circle = View(ctx)
            circle.setLayoutParams(clp)
            cbg = GradientDrawable()
            cbg.setShape(GradientDrawable.OVAL)
            cbg.setStroke(dp(2), divider_color)
            circle.setBackground(cbg)
            row.addView(circle)

        task_tv = TextView(ctx)
        task_tv.setText(task)
        task_tv.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 15)
        if is_done:
            task_tv.setPaintFlags(task_tv.getPaintFlags() | 0x10)
            task_tv.setTextColor(text_color)
        else:
            task_tv.setTextColor(text_color)
        tlp = LinearLayout.LayoutParams(0, WRAP_CONTENT, 1.0)
        task_tv.setLayoutParams(tlp)
        row.addView(task_tv)

        def on_row_click(v, _key=key, _tid=tid):
            if not _plugin_ref:
                return
            data = _msg_data_cache.get(_key)
            if not data:
                return
            m = data.get("mo")
            if m is None:
                return
            if not m.isOut():
                BulletinHelper.show_error(_L("only_author_toggle"))
                return
            _plugin_ref._toggle_task_by_key(_key, _tid)

        row.setOnClickListener(OnClickListener(on_row_click))
        row.setClickable(True)
        card.addView(row, LayoutHelper.createLinear(MATCH_PARENT, WRAP_CONTENT))

    sep2 = View(ctx)
    sep2.setBackgroundColor(divider_color)
    card.addView(sep2, LayoutHelper.createLinear(MATCH_PARENT, 1, 0, 4, 0, 4))

    footer_row = LinearLayout(ctx)
    footer_row.setOrientation(LinearLayout.VERTICAL)
    footer_row.setPadding(0, dp(2), 0, dp(14) if not mo.isOut() else 0)

    done_count = len(parsed["done"])
    total_count = len(parsed["tasks"])
    footer = TextView(ctx)
    footer.setText(_L("completed_count", done=done_count, total=total_count))
    footer.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 13)
    footer.setTextColor(text_color)
    footer_row.addView(footer, LayoutHelper.createLinear(MATCH_PARENT, WRAP_CONTENT))

    if mo.isOut():
        edit_wrap = LinearLayout(ctx)
        edit_wrap.setOrientation(LinearLayout.HORIZONTAL)
        edit_wrap.setGravity(Gravity.CENTER)
        edit_wrap.setPadding(0, dp(8), 0, dp(14))
        edit_wrap.setClickable(True)
        edit_wrap.setFocusable(True)

        edit_btn = TextView(ctx)
        edit_btn.setText(_L("edit_btn"))
        edit_btn.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 13)
        edit_btn.setTextColor(link_color)
        edit_wrap.addView(edit_btn, LayoutHelper.createLinear(WRAP_CONTENT, WRAP_CONTENT))

        def on_edit_click(v, _key=key):
            if not _plugin_ref:
                return
            data = _msg_data_cache.get(_key)
            if not data:
                return
            _mo = data.get("mo")
            _parsed = data.get("parsed")
            if not _mo or not _parsed:
                return
            try:
                from client_utils import get_last_fragment
                frag = get_last_fragment()
                if frag:
                    run_on_ui_thread(lambda: _plugin_ref._show_toggle(frag, _mo, _parsed))
            except Exception as e:
                log("TodoList edit btn: " + str(e))

        edit_wrap.setOnClickListener(OnClickListener(on_edit_click))
        edit_btn.setOnClickListener(OnClickListener(on_edit_click))
        footer_row.addView(edit_wrap, LayoutHelper.createLinear(MATCH_PARENT, WRAP_CONTENT))

    card.addView(footer_row, LayoutHelper.createLinear(MATCH_PARENT, WRAP_CONTENT))

    return card


def _calc_position(cell, mo):
    dp = AndroidUtilities.dp
    tx = dp(12)
    ty = dp(10)
    card_w = dp(260)
    bg_left = 0
    bw = 0
    cell_w = 0

    try:
        cell_w = int(cell.getMeasuredWidth())
        if cell_w <= 0:
            cell_w = int(cell.getWidth())
    except Exception:
        cell_w = 0

    try:
        c = cell.JA
        ty = int(c.textY)
        bw = int(c.backgroundWidth)
        try:
            bg_left = int(c.backgroundDrawableLeft)
        except Exception:
            if cell_w > 0 and mo.isOut():
                bg_left = cell_w - bw
            else:
                bg_left = 0
    except Exception:
        try:
            from hook_utils import get_field
            ty = int(get_field(cell, "textY"))
            bw = int(get_field(cell, "backgroundWidth"))
            try:
                bg_left = int(get_field(cell, "backgroundDrawableLeft"))
            except Exception:
                if cell_w > 0 and mo.isOut():
                    bg_left = cell_w - bw
                else:
                    bg_left = 0
        except Exception:
            pass

    if bw > 0:
        tx = bg_left + dp(10)
        card_w = bw - dp(20)
    if cell_w > 0:
        if tx < dp(4):
            tx = dp(4)
        max_w = cell_w - tx - dp(4)
        if max_w > 0:
            card_w = min(card_w, max_w)
    if card_w < dp(140):
        card_w = dp(140)

    return tx, ty, card_w


def _fix_total_height(cell, mo, ch, key=None):
    try:
        if ch <= 0:
            return
        if key is None:
            key = _get_msg_key(mo)
        text_h = 0
        try:
            text_h = int(mo.textHeight())
        except Exception:
            pass

        current_total = 0
        try:
            current_total = int(cell.JA.totalHeight)
        except Exception:
            try:
                from hook_utils import get_field
                current_total = int(get_field(cell, "totalHeight"))
            except Exception:
                return

        if current_total <= 0:
            return

        cell_id = 0
        try:
            cell_id = cell.hashCode()
        except Exception:
            cell_id = id(cell)

        last_state = _cell_height_state.get(cell_id)
        if last_state and last_state.get("key") == key and last_state.get("modified_total_height") == current_total and last_state.get("ch") == ch:
            return

        new_total = current_total - text_h + ch
        if new_total > 0:
            try:
                cell.JA.totalHeight = new_total
            except Exception:
                try:
                    from hook_utils import set_field
                    set_field(cell, "totalHeight", new_total)
                except Exception:
                    pass
            _cell_height_state[cell_id] = {
                "key": key,
                "base_total_height": current_total,
                "modified_total_height": new_total,
                "ch": ch,
                "text_h": text_h
            }
    except Exception as e:
        log("TodoList fix_total_height: " + str(e))


def _build_topic_reply(peer_id, topic_id):
    if not topic_id or topic_id <= 1:
        return None
    try:
        from org.telegram.messenger import MessageObject, UserConfig
        chat_id = int(-peer_id)
        topic = get_messages_controller().getTopicsController().findTopic(chat_id, int(topic_id))
        if topic is None or topic.topicStartMessage is None:
            return None
        obj = MessageObject(int(UserConfig.selectedAccount), topic.topicStartMessage, False, False)
        if obj.messageOwner is None:
            return None
        _ = obj.getId()
        obj.isTopicMainMessage = True
        return obj
    except Exception:
        return None



# ============================================================
# MaxExteraPlugins Shared Author & Channel Subscription Module
# ============================================================

# ============================================================
# MaxExteraPlugins Shared Author & Channel Subscription Module
# ============================================================
class AuthorChannelHelper:
    CONFIG_URL = "https://raw.githubusercontent.com/MaxExteraPlugins/config/main/links.json"

    DEFAULT_LINKS = {
        "channel_username": "MaxExteraPlugins",
        "channel_url": "https://t.me/MaxExteraPlugins",
        "trial_days": 7,
        "header": {"ru": "MaxExteraPlugins", "en": "MaxExteraPlugins"},
        "buttons": [
            {"title": {"ru": "Канал автора", "en": "Author's Channel"}, "icon": "msg_channel", "url": "https://t.me/MaxExteraPlugins"},
            {"title": {"ru": "Поддержать автора", "en": "Support author"}, "icon": "msg_share", "url": "https://t.me/itNotMax"},
            {"title": {"ru": "Сообщить о баге", "en": "Report a bug"}, "icon": "msg_help", "url": "https://t.me/itNotMax"}
        ]
    }

    _TEXTS = {
        "install_card_title": {"ru": "Спасибо за установку!", "en": "Thank you for installing!"},
        "install_card_msg": {
            "ru": "Надеемся, что плагин будет вам полезен!\n\nМы делаем плагины бесплатными и доступными для всех: пожалуйста, поддержите нас подпиской. Там будут только важные новости, обновления и розыгрыши.",
            "en": "We hope this plugin will be useful to you!\n\nWe keep our plugins free and open for everyone: please support us with a subscription. We only post key news, updates, and giveaways."
        },
        "subscribe_btn": {"ru": "Подписаться", "en": "Subscribe"},
        "remind_later_btn": {"ru": "Напомнить позже", "en": "Remind later"},
        "check_sub_btn": {"ru": "Проверить подписку", "en": "Check subscription"},
        "trial_expired_title": {"ru": "Пожалуйста, подпишитесь на канал", "en": "Please subscribe to the channel"},
        "trial_expired_msg": {
            "ru": "Пожалуйста, подпишитесь на наш официальный канал.\n\nМы делаем плагины бесплатно, ничего не требуя взамен. До подписки функции плагина временно приостановлены.",
            "en": "Please subscribe to our official channel.\n\nWe develop plugins for free and ask nothing in return. Plugin features are paused until you subscribe."
        },
        "sub_thank_you": {"ru": "Спасибо за подписку на наш канал!", "en": "Thank you for subscribing to our channel!"},
        "sub_thank_you_after_expired": {"ru": "Спасибо за подписку на наш канал!\nПлагин продолжит работу!", "en": "Thank you for subscribing to our channel!\nThe plugin will continue working!"},
        "sub_not_found": {"ru": "Подписка не обнаружена. Пожалуйста, подпишитесь на канал.", "en": "Subscription not found. Please subscribe to the channel."},
        "settings_channel": {"ru": "Канал автора", "en": "Author's Channel"},
        "settings_donate": {"ru": "Поддержать автора", "en": "Support author"},
        "settings_bug_report": {"ru": "Сообщить о баге", "en": "Report a bug"}
    }

    @classmethod
    def is_ru(cls) -> bool:
        try:
            from org.telegram.messenger import LocaleController
            cur = str(LocaleController.getInstance().getCurrentLocale().getLanguage() or "").lower()
            if cur.startswith(("ru", "uk", "be")): return True
            if cur: return False
        except Exception:
            pass
        try:
            from java.util import Locale
            code = str(Locale.getDefault().getLanguage() or "").lower()
            if code.startswith(("ru", "uk", "be")): return True
        except Exception:
            pass
        return False

    @classmethod
    def tr(cls, key: str) -> str:
        entry = cls._TEXTS.get(key, {})
        return entry.get("ru" if cls.is_ru() else "en", entry.get("en", key))

    def __init__(self, plugin, icon_sticker=None):
        self.plugin = plugin
        self.icon_sticker = icon_sticker or getattr(plugin, "__icon__", "MaxExteraPluginsStickers/1")
        self._stopped = False
        self._active_dialog = None
        self._last_known_sub = None

    def on_load(self):
        self._stopped = False
        self._active_dialog = None
        self._last_known_sub = None
        self._load_remote_links_async()
        self._check_initial_subscription_flow()
        self._start_subscription_watcher()

    def on_event(self, event_type):
        try:
            name = str(event_type).upper()
            if name.endswith("START") or name.endswith("RESUME"):
                self._check_subscription_change_instant()
        except Exception:
            pass

    def on_unload(self):
        self._stopped = True
        self._dismiss_active_dialog()

    def _get_links(self) -> dict:
        raw = self.plugin.get_setting("remote_links_cache", None)
        if raw:
            try:
                import json
                data = json.loads(raw)
                if isinstance(data, dict): return data
            except Exception:
                pass
        return self.DEFAULT_LINKS

    def _load_remote_links_async(self):
        def worker():
            try:
                import urllib.request, json
                req = urllib.request.Request(self.CONFIG_URL, headers={"User-Agent": "MaxExteraPlugins"})
                with urllib.request.urlopen(req, timeout=4) as resp:
                    if resp.status == 200:
                        data = json.loads(resp.read().decode("utf-8"))
                        if isinstance(data, dict):
                            self.plugin.set_setting("remote_links_cache", json.dumps(data))
                            self._resolve_channel_in_telegram(data.get("channel_username", "MaxExteraPlugins"))
            except Exception:
                pass
        import threading
        t = threading.Thread(target=worker, daemon=True)
        t.start()

    def _open_url(self, url: str, view=None):
        try:
            from org.telegram.messenger.browser import Browser
            from org.telegram.messenger import ApplicationLoader
            from client_utils import get_last_fragment
            ctx = None
            if view is not None:
                ctx = view.getContext()
            if ctx is None:
                frag = get_last_fragment()
                if frag is not None:
                    ctx = frag.getParentActivity()
            if ctx is None:
                ctx = ApplicationLoader.applicationContext
            Browser.openUrl(ctx, url)
        except Exception:
            pass

    def _resolve_channel_in_telegram(self, username: str):
        try:
            from org.telegram.messenger import UserConfig, MessagesController
            from org.telegram.tgnet import TLRPC, ConnectionsManager, RequestDelegate
            clean_user = username.lstrip("@")
            acc = int(UserConfig.selectedAccount)
            mc = MessagesController.getInstance(acc)
            if not mc: return
            req = TLRPC.TL_contacts_resolveUsername()
            req.username = clean_user
            helper_ref = self
            class Delegate(RequestDelegate):
                def run(self, response, error):
                    if error is None and response is not None:
                        chats = getattr(response, "chats", None)
                        if chats is not None and chats.size() > 0:
                            mc.putChats(chats, False)
                            c = chats.get(0)
                            cid = getattr(c, "id", 0)
                            if cid > 0:
                                helper_ref.plugin.set_setting("resolved_channel_id", int(cid))
            ConnectionsManager.getInstance(acc).sendRequest(req, Delegate())
        except Exception:
            pass

    def is_subscribed(self) -> bool:
        try:
            from org.telegram.messenger import UserConfig, MessagesController
            links = self._get_links()
            target = str(links.get("channel_username", "MaxExteraPlugins") or "MaxExteraPlugins").lower().lstrip("@")
            saved_cid = self.plugin.get_setting("resolved_channel_id", 0)

            for acc in range(UserConfig.MAX_ACCOUNT_COUNT):
                uconf = UserConfig.getInstance(acc)
                if not uconf.isClientActivated(): continue
                mc = MessagesController.getInstance(acc)
                if not mc: continue

                if saved_cid:
                    try:
                        from java.lang import Long as JLong
                        c = mc.getChat(JLong(int(saved_cid)))
                        if c is not None:
                            left = bool(getattr(c, "left", True))
                            kicked = bool(getattr(c, "kicked", False))
                            if not left and not kicked: return True
                    except Exception:
                        pass

                try:
                    chat = mc.getUserOrChat(target)
                    if chat is not None:
                        cid = getattr(chat, "id", 0)
                        if cid and not saved_cid:
                            self.plugin.set_setting("resolved_channel_id", int(cid))
                        left = bool(getattr(chat, "left", True))
                        kicked = bool(getattr(chat, "kicked", False))
                        if not left and not kicked: return True
                except Exception:
                    pass

                try:
                    dialogs = mc.allDialogs
                    if dialogs is not None:
                        limit = min(dialogs.size(), 300)
                        for i in range(limit):
                            d = dialogs.get(i)
                            did = getattr(d, "id", 0)
                            if did < 0:
                                from java.lang import Long as JLong
                                c = mc.getChat(JLong(-did))
                                if c is not None:
                                    uname = str(getattr(c, "username", "") or "").lower()
                                    if uname == target:
                                        cid = getattr(c, "id", 0)
                                        if cid and not saved_cid:
                                            self.plugin.set_setting("resolved_channel_id", int(cid))
                                        left = bool(getattr(c, "left", True))
                                        kicked = bool(getattr(c, "kicked", False))
                                        if not left and not kicked: return True
                except Exception:
                    pass
        except Exception:
            pass
        return False

    def is_allowed(self) -> bool:
        import time
        if self.is_subscribed():
            if not self.plugin.get_setting("was_subscribed", False):
                was_exp = bool(self.plugin.get_setting("was_expired_state", False))
                self.plugin.set_setting("was_subscribed", True)
                self.plugin.set_setting("was_expired_state", False)
                self._notify_subscribed(was_expired=was_exp)
            return True

        if self.plugin.get_setting("was_expired_state", False) or self.plugin.get_setting("was_subscribed", False):
            self.plugin.set_setting("was_subscribed", False)
            self.plugin.set_setting("was_expired_state", True)
            self._show_expired_card()
            return False

        now = time.time()
        install_time = float(self.plugin.get_setting("install_time", 0.0) or 0.0)
        if install_time <= 0:
            install_time = now
            self.plugin.set_setting("install_time", install_time)

        trial_days = float(self._get_links().get("trial_days", 7))
        trial_sec = trial_days * 86400.0

        if (now - install_time) < trial_sec:
            return True

        self.plugin.set_setting("was_expired_state", True)
        self._show_expired_card()
        return False

    def prepend_settings(self, original_items=None) -> list:
        from ui.settings import Header, Text, Divider

        # Prevent double-prepending
        if original_items and any(getattr(x, "text", "") == "MaxExteraPlugins" for x in original_items if type(x).__name__ == "Header"):
            return original_items

        links = self._get_links()
        buttons_config = links.get("buttons")

        author_items = []
        if isinstance(buttons_config, list):
            for btn in buttons_config:
                if not isinstance(btn, dict): continue
                url = str(btn.get("url") or "").strip()
                if not url: continue

                title_data = btn.get("title")
                if isinstance(title_data, dict):
                    title = title_data.get("ru" if self.is_ru() else "en") or title_data.get("en") or title_data.get("ru") or ""
                elif isinstance(title_data, str) and title_data:
                    title = title_data
                else:
                    title = btn.get("title_ru" if self.is_ru() else "title_en") or btn.get("title_ru") or btn.get("title_en") or ""

                if not title: continue
                icon = str(btn.get("icon") or "msg_channel").strip()

                def make_click(u):
                    return lambda v=None: self._open_url(u, v)

                author_items.append(Text(text=title, icon=icon, on_click=make_click(url)))
        else:
            for k, text_key, icon_name in [
                ("channel_url", "settings_channel", "msg_channel"),
                ("donate_url", "settings_donate", "msg_share"),
                ("bug_report_url", "settings_bug_report", "msg_help")
            ]:
                u = str(links.get(k) or "").strip()
                if u:
                    author_items.append(Text(text=self.tr(text_key), icon=icon_name, on_click=lambda v=None, target_u=u: self._open_url(target_u, v)))

        res = []
        if author_items:
            hdr = links.get("header") or "MaxExteraPlugins"
            if isinstance(hdr, dict):
                hdr_text = hdr.get("ru" if self.is_ru() else "en") or hdr.get("ru") or hdr.get("en") or "MaxExteraPlugins"
            else:
                hdr_text = str(hdr)
            res.append(Header(text=hdr_text))
            res.extend(author_items)
            res.append(Divider())

        # Clean original_items by removing any old "Информация" / "Information" category
        cleaned_items = []
        if original_items:
            skipping_info = False
            for item in original_items:
                item_cls = type(item).__name__
                if item_cls == "Header":
                    txt = str(getattr(item, "text", "") or getattr(item, "title", "") or "").lower()
                    if "информ" in txt or "inform" in txt:
                        skipping_info = True
                        continue
                    else:
                        skipping_info = False
                elif skipping_info and item_cls == "Divider":
                    skipping_info = False
                    continue

                if not skipping_info:
                    cleaned_items.append(item)

        res.extend(cleaned_items)
        return res

    def _dismiss_active_dialog(self):
        try:
            if self._active_dialog is not None:
                self._active_dialog.dismiss()
        except Exception:
            pass
        self._active_dialog = None

    def _is_dialog_active(self) -> bool:
        try:
            if self._active_dialog is not None:
                return bool(self._active_dialog.isShowing())
        except Exception:
            pass
        return False

    def _notify_subscribed(self, was_expired=False):
        self.plugin.set_setting("was_subscribed", True)
        from ui.bulletin import BulletinHelper
        msg_key = "sub_thank_you_after_expired" if was_expired else "sub_thank_you"
        BulletinHelper.show_success(self.tr(msg_key))

    def _check_subscription_change_instant(self):
        try:
            from android_utils import run_on_ui_thread
            cur_sub = self.is_subscribed()
            prev_sub = self._last_known_sub
            if prev_sub is not None and prev_sub != cur_sub:
                self._last_known_sub = cur_sub
                if cur_sub:
                    was_exp = bool(self.plugin.get_setting("was_expired_state", False))
                    self.plugin.set_setting("was_subscribed", True)
                    self.plugin.set_setting("was_expired_state", False)
                    self._dismiss_active_dialog()
                    self._notify_subscribed(was_expired=was_exp)
                else:
                    self.plugin.set_setting("was_subscribed", False)
                    self.plugin.set_setting("was_expired_state", True)
                    self._dismiss_active_dialog()
                    self._show_expired_card()
            else:
                self._last_known_sub = cur_sub
        except Exception:
            pass

    def _start_subscription_watcher(self):
        def watcher_loop():
            import time
            from android_utils import run_on_ui_thread
            time.sleep(2.0)
            if self._stopped: return
            self._last_known_sub = self.is_subscribed()

            while not self._stopped:
                try:
                    time.sleep(2.0)
                    if self._stopped: break
                    cur_sub = self.is_subscribed()
                    prev_sub = self._last_known_sub

                    if prev_sub is not None and prev_sub != cur_sub:
                        self._last_known_sub = cur_sub
                        if cur_sub:
                            was_exp = bool(self.plugin.get_setting("was_expired_state", False))
                            self.plugin.set_setting("was_subscribed", True)
                            self.plugin.set_setting("was_expired_state", False)
                            def on_sub():
                                self._dismiss_active_dialog()
                                self._notify_subscribed(was_expired=was_exp)
                            run_on_ui_thread(on_sub)
                        else:
                            self.plugin.set_setting("was_subscribed", False)
                            self.plugin.set_setting("was_expired_state", True)
                            def on_unsub():
                                self._dismiss_active_dialog()
                                self._show_expired_card()
                            run_on_ui_thread(on_unsub)
                    else:
                        self._last_known_sub = cur_sub
                except Exception:
                    pass
        import threading
        t = threading.Thread(target=watcher_loop, daemon=True)
        t.start()

    def _check_initial_subscription_flow(self):
        def flow():
            import time
            try:
                now = time.time()
                install_time = float(self.plugin.get_setting("install_time", 0.0) or 0.0)
                if install_time <= 0:
                    install_time = now
                    self.plugin.set_setting("install_time", install_time)

                is_sub = self.is_subscribed()
                self._last_known_sub = is_sub
                was_sub = bool(self.plugin.get_setting("was_subscribed", False))
                was_exp = bool(self.plugin.get_setting("was_expired_state", False))

                if is_sub:
                    if not was_sub:
                        self.plugin.set_setting("was_subscribed", True)
                        self.plugin.set_setting("was_expired_state", False)
                        self._notify_subscribed(was_expired=was_exp)
                    return

                if was_sub or was_exp:
                    self.plugin.set_setting("was_subscribed", False)
                    self.plugin.set_setting("was_expired_state", True)
                    self._show_expired_card()
                    return

                trial_days = float(self._get_links().get("trial_days", 7))
                trial_sec = trial_days * 86400.0
                last_remind = float(self.plugin.get_setting("last_remind_time", 0.0) or 0.0)

                if (now - install_time) < trial_sec:
                    if last_remind <= 0 or (now - last_remind) >= trial_sec:
                        self._show_welcome_card()
                else:
                    self.plugin.set_setting("was_expired_state", True)
                    self._show_expired_card()
            except Exception:
                pass
        from android_utils import run_on_ui_thread
        run_on_ui_thread(flow, 1500)

    def _create_card_content(self, act, title_text, message_text):
        try:
            from android.widget import LinearLayout, TextView
            from android.view import Gravity
            from android.graphics import Typeface
            from org.telegram.messenger import AndroidUtilities, UserConfig, MediaDataController
            from org.telegram.ui.ActionBar import Theme
            from org.telegram.ui.Components import BackupImageView

            dp = AndroidUtilities.dp
            layout = LinearLayout(act)
            layout.setOrientation(LinearLayout.VERTICAL)
            layout.setGravity(Gravity.CENTER_HORIZONTAL)
            layout.setPadding(dp(24), dp(16), dp(24), dp(6))

            size = dp(76)
            iv = BackupImageView(act)
            iv.setRoundRadius(dp(18))
            lp_iv = LinearLayout.LayoutParams(size, size)
            lp_iv.gravity = Gravity.CENTER_HORIZONTAL
            lp_iv.setMargins(0, dp(4), 0, dp(16))
            iv.setLayoutParams(lp_iv)

            try:
                acc = int(UserConfig.selectedAccount)
                mdc = MediaDataController.getInstance(acc)
                raw_icon = str(self.icon_sticker)
                if "/" in raw_icon:
                    pack, idx_s = raw_icon.split("/", 1)
                    mdc.setPlaceholderImageByIndex(iv, pack, int(idx_s), "150_150")
            except Exception:
                pass
            layout.addView(iv)

            if title_text:
                tt = TextView(act)
                tt.setText(title_text)
                tt.setTextSize(19.0)
                tt.setTypeface(None, Typeface.BOLD)
                tt.setTextColor(Theme.getColor(Theme.key_dialogTextBlack))
                tt.setGravity(Gravity.CENTER_HORIZONTAL)
                lp_t = LinearLayout.LayoutParams(-1, -2)
                lp_t.setMargins(0, 0, 0, dp(12))
                tt.setLayoutParams(lp_t)
                layout.addView(tt)

            if message_text:
                mt = TextView(act)
                mt.setText(message_text)
                mt.setTextSize(15.0)
                mt.setTextColor(Theme.getColor(Theme.key_dialogTextBlack))
                mt.setLineSpacing(float(dp(3)), 1.0)
                mt.setGravity(Gravity.CENTER_HORIZONTAL)
                lp_m = LinearLayout.LayoutParams(-1, -2)
                mt.setLayoutParams(lp_m)
                layout.addView(mt)

            return layout
        except Exception:
            return None

    def _show_welcome_card(self):
        def show():
            try:
                if self._is_dialog_active(): return
                from client_utils import get_last_fragment
                frag = get_last_fragment()
                if not frag: return
                act = frag.getParentActivity()
                if not act: return

                links = self._get_links()
                url = links.get("channel_url", "https://t.me/MaxExteraPlugins")

                from ui.alert import AlertDialogBuilder
                b = AlertDialogBuilder(act)
                content = self._create_card_content(act, self.tr("install_card_title"), self.tr("install_card_msg"))
                if content is not None:
                    b.set_view(content)
                else:
                    b.set_title(self.tr("install_card_title"))
                    b.set_message(self.tr("install_card_msg"))

                def on_sub(d, w):
                    self._dismiss_active_dialog()
                    self._open_url(url)
                    def check_after():
                        if self.is_subscribed():
                            self._notify_subscribed(was_expired=False)
                    from android_utils import run_on_ui_thread
                    run_on_ui_thread(check_after, 3000)

                def on_later(d, w):
                    import time
                    self._dismiss_active_dialog()
                    self.plugin.set_setting("last_remind_time", time.time())

                b.set_positive_button(self.tr("subscribe_btn"), on_sub)
                b.set_negative_button(self.tr("remind_later_btn"), on_later)
                self._active_dialog = b.show()
            except Exception:
                pass
        from android_utils import run_on_ui_thread
        run_on_ui_thread(show)

    def _show_expired_card(self):
        def show():
            try:
                if self._is_dialog_active(): return
                from client_utils import get_last_fragment
                frag = get_last_fragment()
                if not frag: return
                act = frag.getParentActivity()
                if not act: return

                links = self._get_links()
                url = links.get("channel_url", "https://t.me/MaxExteraPlugins")

                from ui.alert import AlertDialogBuilder
                from ui.bulletin import BulletinHelper
                b = AlertDialogBuilder(act)
                content = self._create_card_content(act, self.tr("trial_expired_title"), self.tr("trial_expired_msg"))
                if content is not None:
                    b.set_view(content)
                else:
                    b.set_title(self.tr("trial_expired_title"))
                    b.set_message(self.tr("trial_expired_msg"))

                def on_sub(d, w):
                    self._dismiss_active_dialog()
                    self._open_url(url)
                    def check_after():
                        if self.is_subscribed():
                            self.plugin.set_setting("was_subscribed", True)
                            self.plugin.set_setting("was_expired_state", False)
                            self._notify_subscribed(was_expired=True)
                    from android_utils import run_on_ui_thread
                    run_on_ui_thread(check_after, 3000)

                def on_check(d, w):
                    self._dismiss_active_dialog()
                    if self.is_subscribed():
                        self.plugin.set_setting("was_subscribed", True)
                        self.plugin.set_setting("was_expired_state", False)
                        self._notify_subscribed(was_expired=True)
                    else:
                        BulletinHelper.show_error(self.tr("sub_not_found"))
                        from android_utils import run_on_ui_thread
                        run_on_ui_thread(self._show_expired_card, 500)

                b.set_positive_button(self.tr("subscribe_btn"), on_sub)
                b.set_negative_button(self.tr("check_sub_btn"), on_check)
                self._active_dialog = b.show()
            except Exception:
                pass
        from android_utils import run_on_ui_thread
        run_on_ui_thread(show)


class TodoListPlugin(BasePlugin):

    def on_app_event(self, event_type):
        if hasattr(self, "_author_helper"):
            self._author_helper.on_event(event_type)

    def on_plugin_load(self):
        self._author_helper = AuthorChannelHelper(self, icon_sticker="MaxExteraPluginsStickers/21")
        self._author_helper.on_load()
        global _plugin_ref
        _plugin_ref = self
        self.add_menu_item(MenuItemData(
            menu_type=MenuItemType.CHAT_ACTION_MENU,
            text=_L("menu_todo_list", self),
            on_click=self._on_create,
            icon="msg_list",
            item_id="todo_create"
        ))
        self.add_menu_item(MenuItemData(
            menu_type=MenuItemType.MESSAGE_CONTEXT_MENU,
            text=_L("menu_todo_list", self),
            on_click=self._on_ctx_toggle,
            icon="msg_check",
            item_id="todo_toggle"
        ))
        self._setup_hooks()

    def on_plugin_unload(self):
        if hasattr(self, "_author_helper"):
            self._author_helper.on_unload()
        global _plugin_ref, _msg_data_cache, _card_heights, _cell_height_state
        _plugin_ref = None
        _msg_data_cache.clear()
        _card_heights.clear()
        _cell_height_state.clear()

    def _setup_hooks(self):
        if _render_disabled():
            return
        try:
            mo_cls = JClass.forName("org.telegram.messenger.MessageObject")
            cell_cls = JClass.forName("org.telegram.ui.Cells.ChatMessageCell")
            plugin = self

            class TextHook(MethodHook):
                def after_hooked_method(self, param):
                    try:
                        mo = param.thisObject
                        if mo is None or mo.messageOwner is None or mo.messageOwner.message is None:
                            return
                        raw = str(mo.messageOwner.message)
                        if not raw.startswith(TODO_PREFIX):
                            return
                        parsed = parse_todo(raw)
                        if parsed is None:
                            return
                        mt = mo.messageText
                        base_text = str(mt) if mt is not None else raw
                        line_size = AndroidUtilities.dp(15)
                        if line_size <= 0:
                            line_size = 15
                        ssb = SpannableStringBuilder(base_text)
                        ssb.setSpan(ForegroundColorSpan(Color.parseColor("#01000000")), 0, ssb.length(), SPAN_EXCL)
                        ssb.setSpan(AbsoluteSizeSpan(line_size, True), 0, ssb.length(), SPAN_EXCL)
                        mo.messageText = ssb
                    except Exception as e:
                        log("TodoList text hook: " + str(e))

            for m in mo_cls.getDeclaredMethods():
                if str(m.getName()) == "applyEntities":
                    try:
                        self.hook_method(m, TextHook())
                    except Exception:
                        pass

            class CardHook(MethodHook):
                def after_hooked_method(self, param):
                    try:
                        cell = param.thisObject
                        mo = param.args[0]
                        if mo is None or mo.messageOwner is None or mo.messageOwner.message is None:
                            _remove_card(cell)
                            return
                        raw = str(mo.messageOwner.message)
                        if not raw.startswith(TODO_PREFIX):
                            _remove_card(cell)
                            return
                        parsed = parse_todo(raw)
                        if parsed is None:
                            _remove_card(cell)
                            return
                        key = _get_msg_key(mo)
                        if key is None:
                            _remove_card(cell)
                            return
                        _msg_data_cache[key] = {"mo": mo, "parsed": parsed}
                        expected_tag = _make_card_tag(key, raw)
                        existing_tag = _find_card_tag(cell)
                        if existing_tag == expected_tag:
                            existing_card = _find_card(cell)
                            if existing_card is not None:
                                tx, ty, card_w = _calc_position(cell, mo)
                                ch = existing_card.getMeasuredHeight()
                                if ch <= 0:
                                    ch = _card_heights.get(key, 0)
                                if ch > 0:
                                    existing_card.layout(tx, ty, tx + card_w, ty + ch)
                                    existing_card.invalidate()
                                    cell.invalidate()
                                    _fix_total_height(cell, mo, ch, key)
                                    return
                        _remove_card(cell)
                        plugin._attach_card(cell, mo, parsed, key, raw)
                    except Exception as e:
                        log("TodoList card hook: " + str(e))

            class MeasureHook(MethodHook):
                def after_hooked_method(self, param):
                    try:
                        cell = param.thisObject
                        card = _find_card(cell)
                        if card is None:
                            return
                        mo = _get_mo_from_cell(cell)
                        if mo is None:
                            return
                        key = _get_msg_key(mo)
                        if key is None:
                            return
                        ch = card.getMeasuredHeight()
                        if ch <= 0:
                            ch = _card_heights.get(key, 0)
                        if ch > 0:
                            tx, ty, card_w = _calc_position(cell, mo)
                            from android.view import View as V
                            wSpec = V.MeasureSpec.makeMeasureSpec(card_w, V.MeasureSpec.EXACTLY)
                            hSpec = V.MeasureSpec.makeMeasureSpec(ch, V.MeasureSpec.EXACTLY)
                            card.measure(wSpec, hSpec)
                            _fix_total_height(cell, mo, ch, key)
                            try:
                                w = cell.getMeasuredWidth()
                                h = int(cell.JA.totalHeight)
                                if h > 0 and w > 0:
                                    cell.setMeasuredDimension(w, h)
                            except Exception:
                                pass
                    except Exception as e:
                        log("TodoList measure hook: " + str(e))

            class LayoutHook(MethodHook):
                def after_hooked_method(self, param):
                    try:
                        cell = param.thisObject
                        card = _find_card(cell)
                        if card is None:
                            return
                        mo = _get_mo_from_cell(cell)
                        if mo is None:
                            return
                        key = _get_msg_key(mo)
                        if key is None:
                            return
                        ch = card.getMeasuredHeight()
                        if ch <= 0:
                            ch = _card_heights.get(key, 0)
                        if ch > 0:
                            tx, ty, card_w = _calc_position(cell, mo)
                            card.layout(tx, ty, tx + card_w, ty + ch)
                    except Exception as e:
                        log("TodoList layout hook: " + str(e))

            for m in cell_cls.getDeclaredMethods():
                name = str(m.getName())
                if name == "setMessageContent":
                    try:
                        self.hook_method(m, CardHook())
                    except Exception:
                        pass
                elif name == "onMeasure":
                    try:
                        self.hook_method(m, MeasureHook())
                    except Exception:
                        pass
                elif name == "onLayout":
                    try:
                        self.hook_method(m, LayoutHook())
                    except Exception:
                        pass
        except Exception as e:
            log("TodoList setup error: " + str(e))

    def _attach_card(self, cell, mo, parsed, key, raw):
        try:
            ctx = cell.getContext()
            card_tag = _make_card_tag(key, raw)
            card = _build_card(ctx, parsed, mo, key, card_tag)

            tx, ty, card_w = _calc_position(cell, mo)

            from android.view import View as V
            wSpec = V.MeasureSpec.makeMeasureSpec(card_w, V.MeasureSpec.EXACTLY)
            hSpec = V.MeasureSpec.makeMeasureSpec(0, V.MeasureSpec.UNSPECIFIED)
            card.measure(wSpec, hSpec)
            ch = card.getMeasuredHeight()
            _card_heights[key] = ch
            cell.addView(card)
            card.measure(wSpec, hSpec)
            card.layout(tx, ty, tx + card_w, ty + ch)
            card.invalidate()
            cell.invalidate()

            _fix_total_height(cell, mo, ch, key)
        except Exception as e:
            log("TodoList attach: " + str(e))

    def _toggle_task_by_key(self, key, tid):
        try:
            data = _msg_data_cache.get(key)
            if not data:
                return
            mo = data.get("mo")
            if not mo:
                return
            raw = str(mo.messageOwner.message)
            fresh = parse_todo(raw)
            if not fresh:
                return
            d = list(fresh["done"])
            if tid in d:
                d.remove(tid)
            else:
                d.append(tid)
            html = build_html(fresh["title"], fresh["sub"], fresh["tasks"], d)
            run_on_ui_thread(lambda: edit_message(mo, text=html, parse_mode="HTML"))
        except Exception as e:
            log("TodoList toggle: " + str(e))

    def _on_ctx_toggle(self, ctx_dict: Dict[str, Any]):
        frag = ctx_dict.get("fragment")
        msg = ctx_dict.get("message")
        if not frag or not msg:
            return
        try:
            raw = None
            try:
                if msg.messageOwner is not None and msg.messageOwner.message is not None:
                    raw = str(msg.messageOwner.message)
            except Exception:
                pass
            if not raw:
                return
            p = parse_todo(raw)
            if not p:
                return
            if not msg.isOut():
                BulletinHelper.show_error(_L("only_author_edit", self), frag)
                return
            run_on_ui_thread(lambda: self._show_toggle(frag, msg, p))
        except Exception as e:
            log("TodoList ctx: " + str(e))

    def _show_toggle(self, frag, msg, parsed):
        try:
            ctx = frag.getParentActivity()
            if not ctx:
                return
            title = parsed["title"]
            sub = parsed["sub"]
            tasks = parsed["tasks"]
            done = list(parsed["done"])
            bld = AlertDialogBuilder(ctx)
            bld.set_title(TODO_PREFIX + " " + title)
            scroll = ScrollView(ctx)
            cont = LinearLayout(ctx)
            cont.setOrientation(LinearLayout.VERTICAL)
            cont.setPadding(
                AndroidUtilities.dp(24), AndroidUtilities.dp(8),
                AndroidUtilities.dp(24), AndroidUtilities.dp(8))
            states = []
            for i, t in enumerate(tasks):
                tid = i + 1
                is_done = tid in done
                row = LinearLayout(ctx)
                row.setOrientation(LinearLayout.HORIZONTAL)
                row.setGravity(Gravity.CENTER_VERTICAL)
                row.setPadding(0, AndroidUtilities.dp(8), 0, AndroidUtilities.dp(8))
                cs = AndroidUtilities.dp(22)
                c = View(ctx)
                cp = LinearLayout.LayoutParams(cs, cs)
                cp.setMargins(0, 0, AndroidUtilities.dp(14), 0)
                c.setLayoutParams(cp)
                row.addView(c)
                lb = TextView(ctx)
                lb.setText(t)
                lb.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 15)
                lp = LinearLayout.LayoutParams(0, WRAP_CONTENT, 1.0)
                lb.setLayoutParams(lp)
                row.addView(lb)
                st = {"done": is_done, "c": c, "lb": lb}

                def upd(s):
                    bg = GradientDrawable()
                    bg.setShape(GradientDrawable.OVAL)
                    if s["done"]:
                        bg.setColor(_CLR_BLUE)
                        s["lb"].setTextColor(_fg_hint())
                        s["lb"].setPaintFlags(s["lb"].getPaintFlags() | 0x10)
                    else:
                        bg.setStroke(AndroidUtilities.dp(2), _CLR_GRAY)
                        s["lb"].setTextColor(_fg())
                        s["lb"].setPaintFlags(s["lb"].getPaintFlags() & ~0x10)
                    s["c"].setBackground(bg)

                upd(st)

                def on_click(v, s=st):
                    s["done"] = not s["done"]
                    upd(s)

                row.setOnClickListener(OnClickListener(on_click))
                row.setClickable(True)
                states.append(st)
                cont.addView(row, LayoutHelper.createLinear(MATCH_PARENT, WRAP_CONTENT))
            scroll.addView(cont, LayoutHelper.createFrame(MATCH_PARENT, WRAP_CONTENT))
            bld.set_view(scroll)

            def on_save(b, w):
                nd = [idx + 1 for idx, s in enumerate(states) if s["done"]]
                html = build_html(title, sub, tasks, nd)
                try:
                    edit_message(msg, text=html, parse_mode="HTML")
                except Exception as e:
                    log("TodoList save: " + str(e))

            def on_edit(b, w):
                bld.dismiss()
                nd = [idx + 1 for idx, s in enumerate(states) if s["done"]]
                p2 = {"title": title, "sub": sub, "tasks": tasks, "done": nd}
                run_on_ui_thread(lambda: self._show_edit(frag, msg, p2))

            bld.set_positive_button(_L("save_btn", self), on_save)
            bld.set_neutral_button(_L("edit_neutral_btn", self), on_edit)
            bld.set_negative_button(LocaleController.getString(R_tg.string.Cancel), None)
            dialog = bld.show()
            dialog.setCanceledOnTouchOutside(False)
        except Exception as e:
            log("TodoList toggle dialog: " + str(e))

    def _show_edit(self, frag, msg, parsed):
        try:
            ctx = frag.getParentActivity()
            if not ctx:
                return
            ti = []
            bld = AlertDialogBuilder(ctx)
            bld.set_title(_L("edit_todo_title", self))
            scroll = ScrollView(ctx)
            cont = LinearLayout(ctx)
            cont.setOrientation(LinearLayout.VERTICAL)
            cont.setPadding(
                AndroidUtilities.dp(24), AndroidUtilities.dp(8),
                AndroidUtilities.dp(24), AndroidUtilities.dp(8))
            te = EditTextBoldCursor(ctx)
            te.setHint(_L("list_title_hint", self))
            te.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 16)
            te.setTextColor(_fg())
            _safe_set_hint_color(te, _fg_hint())
            te.setSingleLine(True)
            te.setBackground(None)
            te.setPadding(0, AndroidUtilities.dp(8), 0, AndroidUtilities.dp(4))
            te.setText(parsed["title"])
            cont.addView(te, LayoutHelper.createLinear(MATCH_PARENT, WRAP_CONTENT))
            se = EditTextBoldCursor(ctx)
            se.setHint(_L("subtitle_hint", self))
            se.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 14)
            se.setTextColor(_fg())
            _safe_set_hint_color(se, _fg_hint())
            se.setSingleLine(True)
            se.setBackground(None)
            se.setPadding(0, AndroidUtilities.dp(4), 0, AndroidUtilities.dp(8))
            if parsed["sub"]:
                se.setText(parsed["sub"])
            cont.addView(se, LayoutHelper.createLinear(MATCH_PARENT, WRAP_CONTENT))
            dv = View(ctx)
            dv.setBackgroundColor(_divider())
            cont.addView(dv, LayoutHelper.createLinear(MATCH_PARENT, 1, 0, 4, 0, 8))
            tc = LinearLayout(ctx)
            tc.setOrientation(LinearLayout.VERTICAL)
            cont.addView(tc, LayoutHelper.createLinear(MATCH_PARENT, WRAP_CONTENT))

            def add_row(init="", is_done=False):
                if len(ti) >= MAX_TASKS:
                    BulletinHelper.show_error(_L("max_tasks_err", self, max=MAX_TASKS), frag)
                    return
                row = LinearLayout(ctx)
                row.setOrientation(LinearLayout.HORIZONTAL)
                row.setGravity(Gravity.CENTER_VERTICAL)
                row.setPadding(0, AndroidUtilities.dp(4), 0, AndroidUtilities.dp(4))
                ci = View(ctx)
                cs = AndroidUtilities.dp(18)
                cp = LinearLayout.LayoutParams(cs, cs)
                cp.setMargins(0, 0, AndroidUtilities.dp(12), 0)
                ci.setLayoutParams(cp)
                bg = GradientDrawable()
                bg.setShape(GradientDrawable.OVAL)
                if is_done:
                    bg.setColor(_CLR_BLUE)
                else:
                    bg.setStroke(AndroidUtilities.dp(2), _CLR_GRAY)
                ci.setBackground(bg)
                row.addView(ci)
                ed = EditTextBoldCursor(ctx)
                ed.setHint(_L("task_hint", self, num=len(ti) + 1))
                ed.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 15)
                ed.setTextColor(_fg())
                _safe_set_hint_color(ed, _fg_hint())
                ed.setSingleLine(True)
                ed.setBackground(None)
                if init:
                    ed.setText(init)
                if is_done:
                    ed.setPaintFlags(ed.getPaintFlags() | 0x10)
                ep = LinearLayout.LayoutParams(0, WRAP_CONTENT, 1.0)
                ed.setLayoutParams(ep)
                row.addView(ed)
                st = {"done": is_done, "circle": ci}

                def toggle_done(v, s=st, e_ed=ed, e_ci=ci):
                    s["done"] = not s["done"]
                    bg2 = GradientDrawable()
                    bg2.setShape(GradientDrawable.OVAL)
                    if s["done"]:
                        bg2.setColor(_CLR_BLUE)
                        e_ed.setPaintFlags(e_ed.getPaintFlags() | 0x10)
                    else:
                        bg2.setStroke(AndroidUtilities.dp(2), _CLR_GRAY)
                        e_ed.setPaintFlags(e_ed.getPaintFlags() & ~0x10)
                    e_ci.setBackground(bg2)

                ci.setOnClickListener(OnClickListener(toggle_done))
                rb = TextView(ctx)
                rb.setText("✕")
                rb.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 18)
                rb.setTextColor(_fg_hint())
                rb.setPadding(AndroidUtilities.dp(12), 0, 0, 0)
                entry = {"row": row, "input": ed, "state": st}
                ti.append(entry)

                def rm(v, e=entry):
                    if e in ti:
                        ti.remove(e)
                        tc.removeView(e["row"])
                        for idx, x in enumerate(ti):
                            x["input"].setHint(_L("task_hint", self, num=idx + 1))

                rb.setOnClickListener(OnClickListener(rm))
                row.addView(rb)
                tc.addView(row, LayoutHelper.createLinear(MATCH_PARENT, WRAP_CONTENT))

            for i, t in enumerate(parsed["tasks"]):
                add_row(t, (i + 1) in parsed["done"])

            al = TextView(ctx)
            al.setText(_L("add_task_btn", self))
            al.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 15)
            al.setTextColor(_fg_blue())
            al.setPadding(0, AndroidUtilities.dp(12), 0, AndroidUtilities.dp(4))
            al.setOnClickListener(OnClickListener(lambda v: add_row()))
            cont.addView(al, LayoutHelper.createLinear(MATCH_PARENT, WRAP_CONTENT))
            scroll.addView(cont, LayoutHelper.createFrame(MATCH_PARENT, WRAP_CONTENT))
            bld.set_view(scroll)

            def on_save(b, w):
                tt = te.getText().toString().strip()
                if not tt:
                    BulletinHelper.show_error(_L("enter_title_err", self), frag)
                    return
                st = se.getText().toString().strip()
                tasks = []
                done = []
                for idx, e in enumerate(ti):
                    t = e["input"].getText().toString().strip()
                    if t:
                        tasks.append(t[:MAX_TASK_LEN])
                        if e["state"]["done"]:
                            done.append(len(tasks))
                html = build_html(tt, st, tasks, done)
                try:
                    edit_message(msg, text=html, parse_mode="HTML")
                except Exception as e:
                    log("TodoList edit save: " + str(e))

            bld.set_positive_button(_L("save_btn", self), on_save)
            bld.set_negative_button(LocaleController.getString(R_tg.string.Cancel), None)
            dialog = bld.show()
            dialog.setCanceledOnTouchOutside(False)
        except Exception as e:
            log("TodoList edit dialog: " + str(e))

    def _on_create(self, ctx_dict: Dict[str, Any]):
        frag = ctx_dict.get("fragment")
        did = ctx_dict.get("dialog_id")
        if not frag or not did:
            return
        topic_id = 0
        try:
            topic_id = int(frag.getTopicId())
        except Exception:
            pass
        run_on_ui_thread(lambda: self._show_create(frag, did, topic_id))

    def _show_create(self, frag, did, topic_id=0):
        try:
            ctx = frag.getParentActivity()
            if not ctx:
                return
            ti = []
            bld = AlertDialogBuilder(ctx)
            bld.set_title(_L("new_todo_title", self))
            scroll = ScrollView(ctx)
            cont = LinearLayout(ctx)
            cont.setOrientation(LinearLayout.VERTICAL)
            cont.setPadding(
                AndroidUtilities.dp(24), AndroidUtilities.dp(8),
                AndroidUtilities.dp(24), AndroidUtilities.dp(8))
            te = EditTextBoldCursor(ctx)
            te.setHint(_L("list_title_hint", self))
            te.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 16)
            te.setTextColor(_fg())
            _safe_set_hint_color(te, _fg_hint())
            te.setSingleLine(True)
            te.setBackground(None)
            te.setPadding(0, AndroidUtilities.dp(8), 0, AndroidUtilities.dp(4))
            cont.addView(te, LayoutHelper.createLinear(MATCH_PARENT, WRAP_CONTENT))
            se = EditTextBoldCursor(ctx)
            se.setHint(_L("subtitle_hint", self))
            se.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 14)
            se.setTextColor(_fg())
            _safe_set_hint_color(se, _fg_hint())
            se.setSingleLine(True)
            se.setBackground(None)
            se.setPadding(0, AndroidUtilities.dp(4), 0, AndroidUtilities.dp(8))
            cont.addView(se, LayoutHelper.createLinear(MATCH_PARENT, WRAP_CONTENT))
            dv = View(ctx)
            dv.setBackgroundColor(_divider())
            cont.addView(dv, LayoutHelper.createLinear(MATCH_PARENT, 1, 0, 4, 0, 8))
            tc = LinearLayout(ctx)
            tc.setOrientation(LinearLayout.VERTICAL)
            cont.addView(tc, LayoutHelper.createLinear(MATCH_PARENT, WRAP_CONTENT))

            def add_row(init=""):
                if len(ti) >= MAX_TASKS:
                    BulletinHelper.show_error(_L("max_tasks_err", self, max=MAX_TASKS), frag)
                    return
                row = LinearLayout(ctx)
                row.setOrientation(LinearLayout.HORIZONTAL)
                row.setGravity(Gravity.CENTER_VERTICAL)
                row.setPadding(0, AndroidUtilities.dp(4), 0, AndroidUtilities.dp(4))
                ci = View(ctx)
                cs = AndroidUtilities.dp(18)
                cp = LinearLayout.LayoutParams(cs, cs)
                cp.setMargins(0, 0, AndroidUtilities.dp(12), 0)
                ci.setLayoutParams(cp)
                bg = GradientDrawable()
                bg.setShape(GradientDrawable.OVAL)
                bg.setStroke(AndroidUtilities.dp(2), _CLR_GRAY)
                ci.setBackground(bg)
                row.addView(ci)
                ed = EditTextBoldCursor(ctx)
                ed.setHint(_L("task_hint", self, num=len(ti) + 1))
                ed.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 15)
                ed.setTextColor(_fg())
                _safe_set_hint_color(ed, _fg_hint())
                ed.setSingleLine(True)
                ed.setBackground(None)
                if init:
                    ed.setText(init)
                ep = LinearLayout.LayoutParams(0, WRAP_CONTENT, 1.0)
                ed.setLayoutParams(ep)
                row.addView(ed)
                rb = TextView(ctx)
                rb.setText("✕")
                rb.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 18)
                rb.setTextColor(_fg_hint())
                rb.setPadding(AndroidUtilities.dp(12), 0, 0, 0)
                entry = {"row": row, "input": ed}
                ti.append(entry)

                def rm(v, e=entry):
                    if e in ti:
                        ti.remove(e)
                        tc.removeView(e["row"])
                        for idx, x in enumerate(ti):
                            x["input"].setHint(_L("task_hint", self, num=idx + 1))

                rb.setOnClickListener(OnClickListener(rm))
                row.addView(rb)
                tc.addView(row, LayoutHelper.createLinear(MATCH_PARENT, WRAP_CONTENT))

            add_row()
            add_row()
            al = TextView(ctx)
            al.setText(_L("add_task_btn", self))
            al.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 15)
            al.setTextColor(_fg_blue())
            al.setPadding(0, AndroidUtilities.dp(12), 0, AndroidUtilities.dp(4))
            al.setOnClickListener(OnClickListener(lambda v: add_row()))
            cont.addView(al, LayoutHelper.createLinear(MATCH_PARENT, WRAP_CONTENT))
            scroll.addView(cont, LayoutHelper.createFrame(MATCH_PARENT, WRAP_CONTENT))
            bld.set_view(scroll)

            def on_send(b, w):
                tt = te.getText().toString().strip()
                if not tt:
                    BulletinHelper.show_error(_L("enter_title_err", self), frag)
                    return
                if len(tt) > MAX_TITLE_LEN:
                    BulletinHelper.show_error(_L("title_long_err", self), frag)
                    return
                st = se.getText().toString().strip()
                tasks = []
                for e in ti:
                    t = e["input"].getText().toString().strip()
                    if t:
                        tasks.append(t[:MAX_TASK_LEN])
                if not tasks:
                    BulletinHelper.show_error(_L("add_one_task_err", self), frag)
                    return
                html = build_html(tt, st, tasks)
                reply_msg = _build_topic_reply(did, topic_id)
                if reply_msg is not None:
                    send_text(did, html, parse_mode="HTML", replyToMsg=reply_msg, replyToTopMsg=reply_msg)
                else:
                    send_text(did, html, parse_mode="HTML")

            bld.set_positive_button(_L("send_btn", self), on_send)
            bld.set_negative_button(LocaleController.getString(R_tg.string.Cancel), None)
            dialog = bld.show()
            dialog.setCanceledOnTouchOutside(False)
        except Exception as e:
            log("TodoList create: " + str(e))

    def _open_url(self, url):
        def handler(view):
            try:
                from org.telegram.messenger.browser import Browser
                ctx = view.getContext()
                Browser.openUrl(ctx, url)
            except Exception:
                pass
        return handler

    def _on_lang_changed(self, new_index: int):
        try:
            self.set_setting("lang", int(new_index), reload_settings=True)
        except Exception as e:
            log("TodoList lang change: " + str(e))

    def _on_emoji_changed(self, v: str):
        pass

    def create_settings(self):
        try:
            items = self._inner_create_settings()
        except Exception:
            items = []
        if hasattr(self, '_author_helper'):
            return self._author_helper.prepend_settings(items)
        return items

    def _inner_create_settings(self):
        return [
            Header(text=_L("header_loc", self)),
            Selector(
                key="lang",
                text=_L("lang_select", self),
                default=0,
                items=["English", "Русский"],
                icon="msg_translate",
                on_change=self._on_lang_changed,
            ),
            Header(text=_L("header_info", self)),
            Text(
                text=_L("info_channel", self),
                icon="msg_channel",
                on_click=self._open_url("https://t.me/MaxExteraPlugins"),
            ),
            Text(
                text=_L("info_doc", self),
                icon="msg_link",
                on_click=self._open_url("https://telegra.ph/Dokumentaciya-k-plaginu-Todo-List-07-11"),
            ),
            Divider(),
            Header(text=_L("header_custom", self)),
            Input(
                key="emoji_done",
                text=_L("done_emoji_title", self),
                default=DEFAULT_DONE,
                subtext=_L("done_emoji_sub", self, def_emoji=DEFAULT_DONE),
                on_change=self._on_emoji_changed,
            ),
            Input(
                key="emoji_pending",
                text=_L("pending_emoji_title", self),
                default=DEFAULT_PENDING,
                subtext=_L("pending_emoji_sub", self, def_emoji=DEFAULT_PENDING),
                on_change=self._on_emoji_changed,
            ),
        ]
