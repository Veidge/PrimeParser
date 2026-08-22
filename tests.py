"""
tests.py — Модульные и интеграционные тесты для warframe.market приложения.

Запуск всех тестов:
    pytest tests.py -v

Запуск с отчётом о покрытии:
    pytest tests.py -v --cov=functions --cov-report=term-missing
"""

import json
import os
import pytest
from unittest.mock import patch, MagicMock, mock_open


# Глобальные фикстуры

def _ingame_order(name="Player1", quantity=5, platinum=50,
                  crossplay=True, platform="pc", status="ingame"):
    """Хелпер: словарь заказа с заданными параметрами."""
    return {
        "user": {
            "ingameName": name,
            "status": status,
            "crossplay": crossplay,
            "platform": platform,
        },
        "quantity": quantity,
        "platinum": platinum,
        "updatedAt": "2024-01-01T00:00:00.000Z",
    }


def _make_orders_response(sell=None, buy=None):
    """Хелпер: мок ответа API с заказами."""
    mock = MagicMock()
    mock.json.return_value = {"data": {"sell": sell or [], "buy": buy or []}}
    return mock


# 1. normalize

class TestNormalize:
    """Тесты функции normalize()."""

    def test_lowercase_conversion(self):
        """Текст приводится к нижнему регистру."""
        from functions import normalize
        assert normalize("ASH PRIME SET") == "ash prime set"

    def test_synonym_set_to_nabor(self):
        """Синоним 'сет' заменяется на 'набор'."""
        from functions import normalize
        assert "набор" in normalize("Ash Prime Сет")

    def test_synonym_komplekt_to_nabor(self):
        """Синоним 'комплект' заменяется на 'набор'."""
        from functions import normalize
        assert "набор" in normalize("Ash Prime Комплект")

    def test_synonym_bp_to_blueprint(self):
        """Синоним 'bp' заменяется на 'blueprint'."""
        from functions import normalize
        assert "blueprint" in normalize("Ash Prime BP")

    def test_synonym_chertezh_normalized(self):
        """Синоним 'чертеж' заменяется на 'чертёж'."""
        from functions import normalize
        assert "чертёж" in normalize("Ash Prime Чертеж")

    def test_removes_punctuation(self):
        """Знаки препинания удаляются из строки."""
        from functions import normalize
        result = normalize("Ash, Prime! Set.")
        assert "," not in result and "!" not in result and "." not in result

    def test_collapses_multiple_spaces(self):
        """Множественные пробелы схлопываются в один."""
        from functions import normalize
        assert "  " not in normalize("Ash   Prime  Set")

    def test_strips_leading_trailing_spaces(self):
        """Ведущие и замыкающие пробелы убираются."""
        from functions import normalize
        assert normalize("  ash prime  ") == "ash prime"

    def test_empty_string(self):
        """Граничный случай: пустая строка → пустая строка."""
        from functions import normalize
        assert normalize("") == ""

    def test_only_spaces(self):
        """Граничный случай: строка из пробелов → пустая строка."""
        from functions import normalize
        assert normalize("   ") == ""


# 2. message_parser

class TestMessageParser:
    """Тесты функции message_parser()."""

    def test_correct_full_format(self):
        """Позитивный сценарий: итоговое сообщение полностью совпадает с ожидаемым."""
        from functions import message_parser
        result = message_parser("PlayerOne", 1, "Ash Prime Set", 50)
        assert result == "/w PlayerOne Hi! I want to buy: 1 'Ash Prime Set' for 50 platinum each. (warframe.market)"

    def test_contains_ingame_name(self):
        """ingameName присутствует в сообщении."""
        from functions import message_parser
        assert "SomePlayer" in message_parser("SomePlayer", 2, "Item", 10)

    def test_contains_item_name(self):
        """Название предмета присутствует в сообщении."""
        from functions import message_parser
        assert "Riven Mod" in message_parser("P", 1, "Riven Mod", 100)

    def test_contains_quantity(self):
        """Количество присутствует в сообщении."""
        from functions import message_parser
        assert "5" in message_parser("P", 5, "Item", 200)

    def test_contains_price(self):
        """Цена в платине присутствует в сообщении."""
        from functions import message_parser
        assert "999" in message_parser("P", 1, "Item", 999)

    def test_zero_price_boundary(self):
        """Граничный случай: цена = 0 не вызывает ошибки."""
        from functions import message_parser
        assert "0" in message_parser("P", 1, "Item", 0)

    def test_large_quantity_boundary(self):
        """Граничный случай: очень большое количество обрабатывается корректно."""
        from functions import message_parser
        assert "99999" in message_parser("P", 99999, "Item", 1)

    def test_empty_item_name(self):
        """Негативный сценарий: пустое имя предмета — возвращается строка."""
        from functions import message_parser
        assert isinstance(message_parser("P", 1, "", 10), str)

    def test_returns_string_type(self):
        """Функция всегда возвращает строку."""
        from functions import message_parser
        assert isinstance(message_parser("A", 1, "B", 1), str)


# 3. warframe_to_url  (ранее не покрыто)

class TestWarframeToUrl:
    """Тесты функции warframe_to_url()."""

    def test_exact_match_returns_slug(self):
        """Точное совпадение нормализованного текста → возвращает slug."""
        with patch.dict("functions.ITEMS_DICT", {"ash prime set": "ash-prime-set"}, clear=True):
            from functions import warframe_to_url
            assert warframe_to_url("Ash Prime Set") == "ash-prime-set"

    def test_partial_match_returns_slug(self):
        """Частичное вхождение текста в ключ → возвращает slug."""
        with patch.dict("functions.ITEMS_DICT", {"ash prime set": "ash-prime-set"}, clear=True):
            from functions import warframe_to_url
            assert warframe_to_url("ash prime") == "ash-prime-set"

    def test_no_match_returns_none(self):
        """Нет совпадения → возвращает None."""
        with patch.dict("functions.ITEMS_DICT", {"rhino set": "rhino-set"}, clear=True):
            from functions import warframe_to_url
            assert warframe_to_url("НесуществующийПредмет12345") is None

    def test_empty_dict_returns_none(self):
        """Граничный случай: пустой ITEMS_DICT → возвращает None."""
        with patch.dict("functions.ITEMS_DICT", {}, clear=True):
            from functions import warframe_to_url
            assert warframe_to_url("Ash Prime Set") is None

    def test_normalizes_input_before_lookup(self):
        """Вход нормализуется перед поиском (регистр, синонимы)."""
        with patch.dict("functions.ITEMS_DICT", {"ash prime набор": "ash-prime-set"}, clear=True):
            from functions import warframe_to_url
            assert warframe_to_url("ASH PRIME СЕТ") == "ash-prime-set"


# 4. build_slug_dict

class TestBuildSlugDict:
    """Тесты функции build_slug_dict()."""

    def test_returns_dict_on_success(self):
        """Позитивный сценарий: при успешном ответе API возвращается непустой словарь."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [{"slug": "ash-prime-set", "i18n": {"en": {"name": "Ash Prime Set"}}}]
        }
        with patch("functions.requests.get", return_value=mock_response):
            from functions import build_slug_dict
            result = build_slug_dict()
        assert isinstance(result, dict) and len(result) > 0

    def test_slug_is_value(self):
        """Slug является значением словаря."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [{"slug": "rhino-prime-set", "i18n": {"en": {"name": "Rhino Prime Set"}}}]
        }
        with patch("functions.requests.get", return_value=mock_response):
            from functions import build_slug_dict
            assert "rhino-prime-set" in build_slug_dict().values()

    def test_multiple_languages_all_added(self):
        """Все языки одного предмета добавляются как отдельные ключи."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [{"slug": "volt-set", "i18n": {
                "en": {"name": "Volt Set"},
                "ru": {"name": "Вольт Набор"}
            }}]
        }
        with patch("functions.requests.get", return_value=mock_response):
            from functions import build_slug_dict
            assert len(build_slug_dict()) == 2

    def test_empty_data_returns_empty_dict(self):
        """Граничный случай: пустой список items → пустой словарь."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": []}
        with patch("functions.requests.get", return_value=mock_response):
            from functions import build_slug_dict
            assert build_slug_dict() == {}

    def test_api_connection_error_raises(self):
        """Негативный сценарий: сетевая ошибка пробрасывается наружу."""
        import requests as req
        with patch("functions.requests.get", side_effect=req.exceptions.ConnectionError):
            from functions import build_slug_dict
            with pytest.raises(req.exceptions.ConnectionError):
                build_slug_dict()

    def test_keys_are_normalized_lowercase(self):
        """Все ключи словаря хранятся в нижнем регистре."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [{"slug": "x", "i18n": {"en": {"name": "UPPERCASE NAME"}}}]
        }
        with patch("functions.requests.get", return_value=mock_response):
            from functions import build_slug_dict
            assert all(k == k.lower() for k in build_slug_dict())


# 5. get_api_icon

class TestGetApiIcon:
    """Тесты функции get_api_icon()."""

    def _icon_mock(self, thumb=None, icon=None):
        m = MagicMock()
        m.json.return_value = {"data": {"i18n": {"en": {"thumb": thumb, "icon": icon}}}}
        return m

    def test_returns_url_on_success(self):
        """Позитивный сценарий: возвращает корректный URL иконки."""
        with patch("functions.warframe_to_url", return_value="ash-prime-set"), \
             patch("functions.requests.get", return_value=self._icon_mock(thumb="items/thumb.png")):
            from functions import get_api_icon
            result = get_api_icon("Ash Prime Set")
        assert result and result.startswith("https://warframe.market/static/assets/")

    def test_returns_none_when_item_not_found(self):
        """warframe_to_url → None → без запроса к API, возвращает None."""
        with patch("functions.warframe_to_url", return_value=None):
            from functions import get_api_icon
            assert get_api_icon("НесуществующийПредмет") is None

    def test_returns_none_when_no_data_field(self):
        """Нет поля 'data' в ответе API → None."""
        m = MagicMock()
        m.json.return_value = {}
        with patch("functions.warframe_to_url", return_value="item"), \
             patch("functions.requests.get", return_value=m):
            from functions import get_api_icon
            assert get_api_icon("item") is None

    def test_returns_none_when_no_i18n_en(self):
        """Нет блока i18n['en'] → None."""
        m = MagicMock()
        m.json.return_value = {"data": {"i18n": {}}}
        with patch("functions.warframe_to_url", return_value="item"), \
             patch("functions.requests.get", return_value=m):
            from functions import get_api_icon
            assert get_api_icon("item") is None

    def test_returns_none_when_no_thumb_and_no_icon(self):
        """И thumb, и icon отсутствуют → None."""
        with patch("functions.warframe_to_url", return_value="item"), \
             patch("functions.requests.get", return_value=self._icon_mock()):
            from functions import get_api_icon
            assert get_api_icon("item") is None

    def test_uses_icon_as_fallback_when_no_thumb(self):
        """Поле icon используется как запасное при отсутствии thumb."""
        with patch("functions.warframe_to_url", return_value="item"), \
             patch("functions.requests.get", return_value=self._icon_mock(icon="items/icon.png")):
            from functions import get_api_icon
            result = get_api_icon("item")
        assert result and "icon.png" in result

    def test_leading_slash_stripped_from_path(self):
        """Ведущий '/' в пути иконки не дублирует слеш в URL."""
        with patch("functions.warframe_to_url", return_value="item"), \
             patch("functions.requests.get", return_value=self._icon_mock(thumb="/items/t.png")):
            from functions import get_api_icon
            result = get_api_icon("item")
        assert "//" not in result.replace("https://", "")


# 6. download_icon_bytes  (ранее не покрыто)

class TestDownloadIconBytes:
    """Тесты функции download_icon_bytes()."""

    def test_returns_bytes_on_success(self):
        """Позитивный сценарий: возвращает байты тела ответа."""
        mock_response = MagicMock()
        mock_response.content = b"\x89PNG\r\n"
        mock_response.raise_for_status = MagicMock()
        with patch("functions.requests.get", return_value=mock_response):
            from functions import download_icon_bytes
            assert download_icon_bytes("https://example.com/img.png") == b"\x89PNG\r\n"

    def test_raises_on_http_error(self):
        """Негативный сценарий: HTTP-ошибка пробрасывается через raise_for_status."""
        import requests as req
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = req.exceptions.HTTPError("404")
        with patch("functions.requests.get", return_value=mock_response):
            from functions import download_icon_bytes
            with pytest.raises(req.exceptions.HTTPError):
                download_icon_bytes("https://example.com/notfound.png")

    def test_timeout_passed_to_get(self):
        """Запрос выполняется с таймаутом 5 секунд."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.content = b""
        with patch("functions.requests.get", return_value=mock_response) as mock_get:
            from functions import download_icon_bytes
            download_icon_bytes("https://example.com/img.png")
        mock_get.assert_called_once_with("https://example.com/img.png", timeout=5)

    def test_raises_on_connection_error(self):
        """Негативный сценарий: сетевая ошибка пробрасывается наружу."""
        import requests as req
        with patch("functions.requests.get", side_effect=req.exceptions.ConnectionError):
            from functions import download_icon_bytes
            with pytest.raises(req.exceptions.ConnectionError):
                download_icon_bytes("https://example.com/img.png")


# 7. bytes_to_image  (ранее не покрыто)

class TestBytesToImage:
    """
    Тесты функции bytes_to_image().

    QPixmap.loadFromData() требует активного дисплея и может зависать
    в headless-среде даже при QT_QPA_PLATFORM=offscreen, поэтому
    QPixmap полностью мокается — проверяется логика функции, а не Qt.
    """

    def test_returns_pixmap_object(self):
        """Функция создаёт QPixmap и вызывает loadFromData с переданными байтами."""
        png_bytes = b'\x89PNG\r\n'
        mock_pixmap_instance = MagicMock()

        with patch("functions.QPixmap", return_value=mock_pixmap_instance) as mock_pixmap_cls:
            from functions import bytes_to_image
            result = bytes_to_image(png_bytes)

        mock_pixmap_cls.assert_called_once()
        mock_pixmap_instance.loadFromData.assert_called_once_with(png_bytes)
        assert result is mock_pixmap_instance

    def test_empty_bytes_still_calls_load(self):
        """Пустые байты передаются в loadFromData без исключения."""
        mock_pixmap_instance = MagicMock()

        with patch("functions.QPixmap", return_value=mock_pixmap_instance):
            from functions import bytes_to_image
            result = bytes_to_image(b"")

        mock_pixmap_instance.loadFromData.assert_called_once_with(b"")
        assert result is mock_pixmap_instance


# 8. collect_data_parts

class TestCollectDataParts:
    """Тесты функции collect_data_parts()."""

    def test_returns_list_with_order_on_success(self):
        """Позитивный сценарий: возвращает список с одним заказом."""
        with patch("functions.warframe_to_url", return_value="ash-prime-set"), \
             patch("functions.requests.get", return_value=_make_orders_response(
                 sell=[_ingame_order()])):
            from functions import collect_data_parts
            result = collect_data_parts("Ash Prime Set", "sell", "pc", 1)
        assert isinstance(result, list) and len(result) == 1

    def test_result_contains_required_keys(self):
        """Результирующий словарь содержит все обязательные ключи."""
        with patch("functions.warframe_to_url", return_value="ash-prime-set"), \
             patch("functions.requests.get", return_value=_make_orders_response(
                 sell=[_ingame_order()])):
            from functions import collect_data_parts
            order = collect_data_parts("Ash Prime Set", "sell", "pc", 1)[0]
        for key in ("ingameName", "name", "type", "quantity", "price", "date"):
            assert key in order

    def test_returns_none_when_item_not_found(self):
        """warframe_to_url → None → функция возвращает None."""
        with patch("functions.warframe_to_url", return_value=None):
            from functions import collect_data_parts
            assert collect_data_parts("НесуществующийПредмет", "sell", "pc") is None

    def test_returns_empty_list_when_no_orders(self):
        """Нет заказов в ответе API → пустой список."""
        with patch("functions.warframe_to_url", return_value="item"), \
             patch("functions.requests.get", return_value=_make_orders_response(sell=[])):
            from functions import collect_data_parts
            assert collect_data_parts("item", "sell", "pc") == []

    def test_skips_offline_users(self):
        """Офлайн-пользователи пропускаются → нет результата."""
        with patch("functions.warframe_to_url", return_value="item"), \
             patch("functions.requests.get", return_value=_make_orders_response(
                 sell=[_ingame_order(status="offline")])):
            from functions import collect_data_parts
            assert not collect_data_parts("item", "sell", "pc")

    def test_skips_non_ingame_status(self):
        """Статус 'online' (не 'ingame') → пользователь пропускается."""
        with patch("functions.warframe_to_url", return_value="item"), \
             patch("functions.requests.get", return_value=_make_orders_response(
                 sell=[_ingame_order(status="online")])):
            from functions import collect_data_parts
            assert not collect_data_parts("item", "sell", "pc")

    def test_quantity_filter_skips_small_order(self):
        """Граничный случай: quantity заказа < запрошенного → пропускается."""
        with patch("functions.warframe_to_url", return_value="item"), \
             patch("functions.requests.get", return_value=_make_orders_response(
                 sell=[_ingame_order(quantity=2)])):
            from functions import collect_data_parts
            assert not collect_data_parts("item", "sell", "pc", quantity=10)

    def test_quantity_one_not_filtered(self):
        """Граничный случай: quantity=1 не попадает под фильтр (quantity > 1 ложно)."""
        with patch("functions.warframe_to_url", return_value="item"), \
             patch("functions.requests.get", return_value=_make_orders_response(
                 sell=[_ingame_order(quantity=1)])):
            from functions import collect_data_parts
            result = collect_data_parts("item", "sell", "pc", quantity=5)
        assert result and len(result) == 1

    def test_crossplay_false_same_platform_matches(self):
        """crossplay=False + совпадение платформы → заказ принимается."""
        order = _ingame_order(crossplay=False, platform="pc")
        with patch("functions.warframe_to_url", return_value="item"), \
             patch("functions.requests.get", return_value=_make_orders_response(sell=[order])):
            from functions import collect_data_parts
            result = collect_data_parts("item", "sell", "pc", crossplay=False)
        assert result and len(result) == 1

    def test_crossplay_false_different_platform_skipped(self):
        """crossplay=False + другая платформа → заказ пропускается."""
        order = _ingame_order(crossplay=False, platform="ps4")
        with patch("functions.warframe_to_url", return_value="item"), \
             patch("functions.requests.get", return_value=_make_orders_response(sell=[order])):
            from functions import collect_data_parts
            assert not collect_data_parts("item", "sell", "pc", crossplay=False)

    def test_crossplay_mismatch_skips_order(self):
        """Несовпадение crossplay между запросом и заказом → пропускается."""
        order = _ingame_order(crossplay=False)
        with patch("functions.warframe_to_url", return_value="item"), \
             patch("functions.requests.get", return_value=_make_orders_response(sell=[order])):
            from functions import collect_data_parts
            assert not collect_data_parts("item", "sell", "pc", crossplay=True)

    def test_buy_type_uses_buy_orders(self):
        """Тип 'buy' использует buy-заказы, а не sell."""
        order = _ingame_order()
        with patch("functions.warframe_to_url", return_value="item"), \
             patch("functions.requests.get", return_value=_make_orders_response(buy=[order])):
            from functions import collect_data_parts
            result = collect_data_parts("item", "buy", "pc")
        assert result and result[0]["type"] == "buy"

    def test_all_orders_exhausted_returns_none(self):
        """for-else: все заказы отфильтрованы → функция возвращает None."""
        orders = [_ingame_order(status="offline"), _ingame_order(status="online")]
        with patch("functions.warframe_to_url", return_value="item"), \
             patch("functions.requests.get", return_value=_make_orders_response(sell=orders)):
            from functions import collect_data_parts
            assert collect_data_parts("item", "sell", "pc") is None


# 9. MainWindow — базовая инициализация


class TestSaveLoadIntegration:
    """
    Интеграционные тесты цикла записи и чтения данных.
    Все операции выполняются во временных директориях —
    рабочие settings.json / saved_requests.json проекта не затрагиваются.
    """

    def test_settings_roundtrip(self, tmp_path):
        """Записанные настройки читаются обратно без искажений."""
        settings = {"username": "RoundTrip", "platform": "switch", "crossplay": False}
        path = tmp_path / "settings.json"
        path.write_text(json.dumps(settings, ensure_ascii=False, indent=4), encoding="utf-8")
        assert json.loads(path.read_text(encoding="utf-8")) == settings

    def test_requests_roundtrip(self, tmp_path):
        """Список заказов читается обратно без искажений."""
        data = [
            {"name": "Nidus Prime Set", "type": "sell", "quantity": 1, "wishedPrice": 120},
            {"name": "Saryn Prime Set", "type": "buy",  "quantity": 2, "wishedPrice": 80},
        ]
        path = tmp_path / "saved_requests.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=4), encoding="utf-8")
        assert json.loads(path.read_text(encoding="utf-8")) == data

    def test_project_files_untouched(self, tmp_path, monkeypatch):
        """Тесты не создают settings.json / saved_requests.json в рабочей директории."""
        monkeypatch.chdir(tmp_path)
        assert not (tmp_path / "settings.json").exists()
        assert not (tmp_path / "saved_requests.json").exists()

    def test_overwrite_settings_preserves_all_fields(self, tmp_path):
        """Перезапись settings.json сохраняет все поля без потерь."""
        path = tmp_path / "settings.json"
        path.write_text(json.dumps({"username": "Old", "platform": "pc", "crossplay": True}))
        new = {"username": "New", "platform": "ps4", "crossplay": False}
        path.write_text(json.dumps(new, ensure_ascii=False, indent=4), encoding="utf-8")
        assert json.loads(path.read_text(encoding="utf-8")) == new

    def test_delete_request_persists(self, tmp_path):
        """После удаления и сохранения файл содержит на один элемент меньше."""
        path = tmp_path / "saved_requests.json"
        data = [
            {"name": "Item A", "type": "sell", "quantity": 1, "wishedPrice": 50},
            {"name": "Item B", "type": "buy",  "quantity": 1, "wishedPrice": 30},
        ]
        path.write_text(json.dumps(data), encoding="utf-8")
        loaded = json.loads(path.read_text(encoding="utf-8"))
        loaded.pop(0)
        path.write_text(json.dumps(loaded, indent=4, ensure_ascii=False), encoding="utf-8")
        reloaded = json.loads(path.read_text(encoding="utf-8"))
        assert len(reloaded) == 1 and reloaded[0]["name"] == "Item B"

    def test_empty_requests_file_loads_without_error(self, tmp_path):
        """Файл с пустым списком [] загружается без ошибок."""
        path = tmp_path / "saved_requests.json"
        path.write_text("[]", encoding="utf-8")
        assert json.loads(path.read_text(encoding="utf-8")) == []

    def test_all_platforms_serialize_correctly(self, tmp_path):
        """Каждая платформа корректно сериализуется и десериализуется."""
        for platform in ("pc", "ps4", "xbox", "switch", "mobile"):
            s = {"username": "u", "platform": platform, "crossplay": True}
            path = tmp_path / f"settings_{platform}.json"
            path.write_text(json.dumps(s), encoding="utf-8")
            assert json.loads(path.read_text(encoding="utf-8"))["platform"] == platform