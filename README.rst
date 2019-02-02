poptimizer
==========
.. image:: https://travis-ci.org/WLM1ke/poptimizer.svg?branch=master
    :target: https://travis-ci.org/WLM1ke/poptimizer
.. image:: https://codecov.io/gh/WLM1ke/poptimizer/branch/master/graph/badge.svg
    :target: https://codecov.io/gh/WLM1ke/poptimizer
.. image:: https://badge.fury.io/py/poptimizer.svg
    :target: https://badge.fury.io/py/poptimizer

Оптимизация долгосрочного портфеля акций.

Основные особенности
--------------------

* Возможность анализа всех акций, обращающихся на MOEX
* База данных по дивидендам с 2010г по десяткам наиболее ликвидных акций
* Использование робастной оптимизации вместо классического mean-variance анализа
* Устойчивые оценки ковариационной матрицы для большого числа акций в портфеле с помощью асимптотически оптимального сжатия Ledoit-Wolf к матрице с малым количеством оцениваемых параметров - с разной дисперсией и одинаковой корреляцией
* Использование машинного обучения для предсказания доходности на основе известных в академической литературе рыночных аномалий

Установка
---------

.. code-block:: Bash

   $ pip install poptimizer

Документация
------------
Часть информации размещена на странице https://wlm1ke.github.io/poptimizer/ - в перспективе будет
дополнена.
