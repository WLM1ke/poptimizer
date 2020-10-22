Оптимизация долгосрочного портфеля акций
========================================
.. image:: https://github.com/WLM1ke/poptimizer/workflows/tests/badge.svg
    :target: https://github.com/WLM1ke/poptimizer/actions
.. image:: https://codecov.io/gh/WLM1ke/poptimizer/branch/master/graph/badge.svg
    :target: https://codecov.io/gh/WLM1ke/poptimizer

Основные особенности
--------------------

Источники данных
^^^^^^^^^^^^^^^^

* Возможность анализа всех акций, обращающихся на MOEX
* База данных дивидендов с 2015г по ~100 наиболее ликвидным акциям
* Возможность сверки базы данных дивидендов с информацией на сайтах:

 - `www.dohod.ru <https://www.dohod.ru/ik/analytics/dividend>`_
 - `www.conomy.ru <https://www.conomy.ru/dates-close/dates-close2>`_
 - `bcs-express.ru <https://bcs-express.ru/dividednyj-kalendar>`_
 - `www.smart-lab.ru <https://smart-lab.ru/dividends/index/order_by_yield/desc/>`_


Прогнозирование параметров активов
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* Использование нейронных сетей на основе архитектуры `WaveNet <https://arxiv.org/abs/1609.03499>`_ с большим receptive field для анализа длинных последовательностей котировок
* Совместное прогнозирование ожидаемой доходности и дисперсии с помощью подходов, базирующихся на `GluonTS: Probabilistic Time Series Models in Python <https://arxiv.org/abs/1906.05264>`_
* Использование устойчивых оценок исторических корреляционных матриц для большого числа активов с помощью сжатия `Ledoit-Wolf <http://www.ledoit.net/honey.pdf>`_

Оптимизация портфеля
^^^^^^^^^^^^^^^^^^^^

* Максимизация приближенного значения геометрической доходности, полученного с помощью `корректировки Йенсена <https://en.wikipedia.org/wiki/Jensen%27s_inequality>`_ для арифметической доходности портфеля
* Поддержание популяции моделей для оценки достоверности прогнозов и поиска гиперпараметров нейронных сетей с использование `дифференциальной эволюции <https://en.wikipedia.org/wiki/Differential_evolution>`_
* Использование робастной инкрементальной оптимизации портфеля на основе расчета вероятности улучшения доходности портфеля в результате торговли с учетом неточности имеющихся прогнозов вместо классической mean-variance оптимизации
* Использование `критерия знаковых рангов Вилкоксона <https://en.wikipedia.org/wiki/Wilcoxon_signed-rank_test>`_ и `поправки Бонферрони <https://en.wikipedia.org/wiki/Bonferroni_correction>`_ на множественное тестирование для оценки вероятности улучшения доходности в результате торговли для портфеля, содержащего большое количество активов

Направления дальнейшего развития
--------------------------------

* Рефакторинг кода на основе `DDD <https://en.wikipedia.org/wiki/Domain-driven_design>`_, `MyPy <http://mypy.readthedocs.org/en/latest/>`_ и `wemake <https://wemake-python-stylegui.de/en/latest/>`_
* Возможность анализа иностранных акций, обращающихся на MOEX
* Возможность анализа ETF, обращающихся на MOEX
* Использование смеси логнормальных распределений вместо нормального распределения для прогнозирования доходности и дисперсии активов
* Применение нелинейного сжатия Ledoit-Wolf для оценки корреляции активов
* Поиск оптимальной архитектуры сетей с помощью эволюции с "нуля" по аналогии с `Evolving Neural Networks through Augmenting Topologies <http://nn.cs.utexas.edu/downloads/papers/stanley.ec02.pdf>`_
* Использование Reinforcement learning для построения портфеля, вместо прямой оптимизации
