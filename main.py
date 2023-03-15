import asyncio
import aiohttp
import tabulate
import numpy

HTTP_OK = 200

# Получаем информацию от api.binance.com
# args:
# symbol - пара, фьючерс или иной актив
# ask - сам запрос
# search - интересующие нас поля информации в полученном ответе
async def get_api(**kwargs):
    api_request = 'https://api.binance.com/api/v3/ticker/'
    if "ask" in kwargs:
        api_request = api_request + kwargs["ask"]
    if "symbol" in kwargs:
        api_request = api_request + "symbol=" + kwargs["symbol"]
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_request) as response:
                if response.status == HTTP_OK:
                    data = await response.json()
                    if "search" in kwargs:
                        result = float(data[kwargs["search"]])
                        return result
                    return data
    except Exception as e:
        print(f'Произошла ошибка: {e}')


async def main():
    # История текущих цен фьючерсов
    ETHUSDT_price = [await get_api(symbol="ETHUSDT", ask="price?", search="price")]
    BTCUSDT_price = [await get_api(symbol="BTCUSDT", ask="price?", search="price")]
    # Объем торговли Примечание: цифры очень странные, подозреваю, что это не совсем за последние 24 часа,
    # а с начала суток, но другого способа не нашел
    ETHUSDT_volume = await get_api(symbol="ETHUSDT", ask="24hr?", search="quoteVolume")
    BTCUSDT_volume = await get_api(symbol="BTCUSDT", ask="24hr?", search="quoteVolume")
    # Количество шагов, в течение которых программа хранит данные (1 шаг - 10 сек)
    num_of_steps = 360

    await asyncio.sleep(10)

    while True:
        try:
            # Получаем информацию от api.binance.com
            ETHUSDT_price.insert(0, await get_api(symbol="ETHUSDT", ask="price?", search="price"))
            BTCUSDT_price.insert(0, await get_api(symbol="BTCUSDT", ask="price?", search="price"))
            ETHUSDT_volume = await get_api(symbol="ETHUSDT", ask="24hr?", search="quoteVolume")
            BTCUSDT_volume = await get_api(symbol="BTCUSDT", ask="24hr?", search="quoteVolume")
            # Если программа работает больше установленного периода - удаляем устаревшие данные
            if len(ETHUSDT_price) == num_of_steps:
                ETHUSDT_price.pop(num_of_steps - 1)
                BTCUSDT_price.pop(num_of_steps - 1)

            # "Сырое" изменение цены ETHUSDT без учета BTCUSDT
            # Сравниваю с тем, что было час назад или меньше, если программа работала недостаточно
            ETHUSDT_price_raw_diff = round((ETHUSDT_price[0] - ETHUSDT_price[-1]) / ETHUSDT_price[-1] * 100, 5)
            # Вычисляю коэффициент корреляции фьючерсов
            ETHUSDT_BTCUSDT_correlation = numpy.corrcoef(ETHUSDT_price, BTCUSDT_price)[0, 1]
            # Сравниваю колличество торгуемой валюты для того, чтобы определить степень влияния одной на другую
            ETHUSDT_BTCUSDT_weight = ETHUSDT_volume / (ETHUSDT_volume + BTCUSDT_volume)
            # Для исключения влияния цены BTCUSDT на ETHUSDT я умножаю сырое изменение цены на коэффициент корреляции
            # и на разницу а объемах торговли. Фьючерс, торгующийся в большем объеме (BTCUSDT), соответственно,
            # влияет в большей степени, однако, существует и обратный эффект, поэтому я и добавил
            # ETHUSDT_BTCUSDT_weight, отражающий отношение объемов торговли этих фьючерсов. Конечно,
            # мой метод анализа примитивен, но я все-таки не экономист. Для полного анализа я бы попробовал взять
            # столько информации с binance, сколько вместилось бы в пропускную способность api, а еще лучше историю
            # за, скажем, полгода, и провел бы регрессионный анализ, затем исключил бы мультиколлинеарность. Но это
            # все же тестовое задание
            ETHUSDT_price_clear_diff = ETHUSDT_price_raw_diff * ETHUSDT_BTCUSDT_correlation * ETHUSDT_BTCUSDT_weight

            # Для более подробных значений
            # data = [
            #     ['ETHUSDT_price', 'BTCUSDT_price', 'ETHUSDT_price_raw_diff', 'ETHUSDT_BTCUSDT_correlation', 'ETHUSDT_BTCUSDT_weight', 'ETHUSDT_price_clear_diff'],
            #     [ETHUSDT_price[0], BTCUSDT_price[0], ETHUSDT_price_raw_diff, ETHUSDT_BTCUSDT_correlation, ETHUSDT_BTCUSDT_weight, ETHUSDT_price_clear_diff]
            # ]
            # Вывод в табличку
            data = [
                ['ETHUSDT_price', 'BTCUSDT_price', 'ETHUSDT_price_raw_diff (%)', 'ETHUSDT_price_clear_diff (%)',
                 'ETHUSDT_price[-1] (Час назад)'],
                [ETHUSDT_price[0], BTCUSDT_price[0], ETHUSDT_price_raw_diff, ETHUSDT_price_clear_diff,
                 ETHUSDT_price[-1]]
            ]
            results = tabulate.tabulate(data)
            print(results)

            # Для отладки, можно увеличить ETHUSDT_price_clear_diff в несколько раз, для проверки работоспособности
            ETHUSDT_price_clear_diff *= 50
            if abs(ETHUSDT_price_clear_diff) >= 1:
                print(
                    f'-----!!!!! За последний час цена ETHUSDT изменилась на {round(ETHUSDT_price_clear_diff), 5} Процента !!!!!-----')
            # Задержка запросов
            await asyncio.sleep(10)
        except Exception as e:
            print(f'Произошла ошибка: {e}')


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Выход из программы...")
