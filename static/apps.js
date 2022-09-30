window.pagesApp = function () {
    "use strict";

    return {
        selectedSection: this.$persist("Tickers").as("page_selected"),
        sections: ["Tickers", "Accounts", "Portfolio", "Metrics", "Optimizer", "Dividends", "Reports"],

        isSelectedSection(section) {
            return section === this.selectedSection;
        },
        selectSection(section) {
            this.selectedSection = section;
        }
    };
};

function formatInt(number) {
    "use strict";

    return new Intl.NumberFormat('ru-RU',
        {maximumFractionDigits: 0})
        .format(number);
}

function formatFrac(number) {
    "use strict";

    return new Intl.NumberFormat('ru-RU')
        .format(number);
}

function formatPercent(number) {
    "use strict";

    return new Intl.NumberFormat('ru-RU',
        {style: "percent", minimumFractionDigits: 2, maximumFractionDigits: 2})
        .format(number);
}

window.tickersApp = function () {
    "use strict";

    return {
        sec: [],
        prefix: "",
        status: "Initialising",

        init() {
            fetch("/tickers")
                .then(async resp => {
                    return resp.ok ? resp.json() : Promise.reject(await resp.text());
                })
                .then(json => {
                    this.sec = json;
                    this.prefix = "";
                    this.status = "Not edited";
                })
                .catch(err => {
                    this.sec = [];
                    this.prefix = "";
                    this.status = err;
                });
        },
        notSelected(ticker) {
            const prefix = this.prefix.toUpperCase();

            return prefix && !ticker.selected && ticker.ticker.startsWith(prefix);
        },
        add(id) {
            this.sec[id].selected = true;
            this.status = "Edited";
        },
        remove(id) {
            this.sec[id].selected = false;
            this.status = "Edited";
        },
        get count() {
            return Array.isArray(this.sec)?
                this.sec.reduce((count, ticker) => count + ticker.selected, 0) :
                0;
        },
        get showButton() {
            return  !["Initialising", "Not edited", "Saved successfully"].includes(this.status);
        },
        async save() {
            this.status = "Saving";

            fetch("/tickers", {
                method: "PUT",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify(this.sec)
            }).then( async resp => {
                this.status = resp.ok ? "Saved successfully" : await resp.text();
            }).catch(err => {
                this.status = err;
            });
        },
    };
};


window.accountsApp = function () {
    "use strict";

    return {
        accounts: [],
        accountNew: "",

        selectedAccount: this.$persist("").as("accounts_selected"),

        cash: 0,
        positions: [],

        positionsSort:  this.$persist("tickers").as("accounts_sort"),
        hideZero:  this.$persist(false).as("accounts_hide_zero"),

        status: "Initialising",

        init() {
            if (this.selectedAccount !== "") {
                this.selectAccount(this.selectedAccount);
            } else {
                this.status = "Account not selected";
            }

            fetch("/accounts")
                .then(async resp => {
                    return resp.ok ? resp.json() : Promise.reject(await resp.text());
                })
                .then(json => {
                    this.accounts = json || [];
                })
                .catch(err => {
                    this.accounts = [];
                    this.status = err;
                });
        },

        createAccount() {
            fetch(`/accounts/${this.accountNew}`, {
                method: "POST",
            }).then( async resp => {
                if (!resp.ok) {
                    return Promise.reject(await resp.text());
                }

                this.accounts.push(this.accountNew);
                this.accounts.sort();

                this.selectAccount(this.accountNew);

                this.accountNew = "";

                this.status = "Created successfully";
            }).catch(err => {
                this.status = err;
            });
        },

        selectAccount(name) {
            fetch(`/accounts/${name}`)
                .then(async resp => {
                    return resp.ok ? resp.json() : Promise.reject(await resp.text());
                })
                .then(json => {
                    this.selectedAccount = name;

                    this.cash = json.cash;
                    this.positions = json.positions;

                    this.status = "Not edited";
                })
                .catch(err => {
                    this.status = err;
                });
        },

        showPos(pos) {
          return !this.hideZero || pos.shares > 0;
        },

        sortedPositions() {
          if (this.positionsSort === "tickers") {
              this.positions.sort((a, b) => a.ticker.localeCompare(b.ticker));
          } else {
              this.positions.sort((a, b) => this.positionValue(b) - this.positionValue(a));
          }

          return this.positions;
        },

        positionValue(pos) {
            return pos.shares * pos.price;
        },

        positionValueFormatted(pos) {
            return formatInt(this.positionValue(pos));
        },

        get showAccount() {
            return this.accounts.includes(this.selectedAccount);
        },

        get count() {
            return this.positions.filter(pos => pos.shares > 0).length;
        },

        get value() {
            return this.positions.reduce((previous, pos) => previous + this.positionValue(pos), this.cash);
        },

        get valueFormatted() {
            return formatInt(this.value);
        },

        deleteAccount() {
            fetch(`/accounts/${this.selectedAccount}`, {
                method: "DELETE",
            }).then(async resp => {
                if (!resp.ok) {
                    return Promise.reject(await resp.text());
                }

                this.accounts = this.accounts.filter(acc => acc !== this.selectedAccount);
                this.selectedAccount = "";

                this.cash = 0;
                this.positions = [];

                this.status = "Deleted successfully";
            }).catch(err => {
                this.status = err;
            });
        },

        save() {
            this.status = "Saving";

            const positions = this.positions
                    .map(pos => {
                        return {ticker: pos.ticker, shares: pos.shares};
                    });

            const account = {"cash": this.cash, "positions": positions}

            fetch(`/accounts/${this.selectedAccount}`, {
                method: "PUT",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify(account)
            }).then( async resp => {
                this.status = resp.ok ? "Saved successfully" : await resp.text();
            }).catch(err => {
                this.status = err;
            });
        },

        edited() {
            this.status = "Edited";
        },

        get showButton() {
            return ![
                "Initialising",
                "Account not selected",
                "Not edited",
                "Created successfully",
                "Saved successfully",
                "Deleted successfully",
            ].includes(this.status);
        },
    };
};


window.portfolioApp = function () {
    "use strict";

    return {
        dates: [],

        selectedDate: this.$persist("").as("portfolio_selected"),

        cash: 0,
        positions: [],
        count: 0,
        effectiveCount: 0,
        value: 0,

        positionsSort:  this.$persist("value").as("portfolio_sort"),
        hideZero:  this.$persist(true).as("portfolio_hide_zero"),

        status: "Initialising",

        init() {
            if (this.selectedDate !== "") {
                this.selectPortfolio(this.selectedDate);
            } else {
                this.status = "Date not selected";
            }

            fetch("/portfolio")
                .then(async resp => {
                    return resp.ok ? resp.json() : Promise.reject(await resp.text());
                })
                .then(json => {
                    this.dates = json || [];
                    this.dates.sort((a, b) => b.localeCompare(a));
                })
                .catch(err => {
                    this.dates = [];
                    this.status = err;
                });
        },

        selectPortfolio(date) {
            fetch(`/portfolio/${date}`)
                .then(async resp => {
                    return resp.ok ? resp.json() : Promise.reject(await resp.text());
                })
                .then(json => {
                    this.selectedDate = date;

                    this.cash = json.cash;
                    this.positions = json.positions;

                    this.count = this.positions.filter(pos => pos.shares > 0).length;

                    const value = this.positions
                        .reduce((previous, pos) => previous + pos.shares * pos.price, this.cash);
                    this.value = value;

                    this.positions.forEach(function(pos) {
                        pos.value = pos.shares * pos.price;
                        pos.weight = pos.value / value;
                    });

                    this.effectiveCount = 0;
                    if (this.count) {
                        this.effectiveCount = formatInt(1 / this.positions
                            .reduce((previous, pos) => previous + (pos.value / (this.value - this.cash)) ** 2, 0));
                    }

                    this.status = `Loaded portfolio for ${date}`;
                })
                .catch(err => {
                    this.status = err;
                });
        },

        showPos(pos) {
            return !this.hideZero || pos.shares > 0;
        },

        sortedPositions() {
            if (this.positionsSort === "tickers") {
                this.positions.sort((a, b) => a.ticker.localeCompare(b.ticker));
            } else if (this.positionsSort === "turnover"){
                this.positions.sort((a, b) => b.turnover - a.turnover);
            } else {
                this.positions.sort((a, b) => b.value - a.value);
            }

            return this.positions;
        },

        positionValueFormatted(pos) {
            return formatInt(pos.value);
        },

        get weightCashFormatted() {
            return formatPercent(this.cash / this.value);
        },

        weightFormatted(pos) {
            return formatPercent(pos.weight);
        },

        get showPortfolio() {
            return this.dates.includes(this.selectedDate);
        },

        get valueFormatted() {
            return formatInt(this.value);
        },
    };
};


window.dividendsApp = function () {
    "use strict";

    return {
        prefix: "",
        sec: [],
        selectedTicker: this.$persist("").as("dividends_selected"),
        dividends: [],
        newDate: "",
        newValue: "",
        newCurrency: "",
        status: "Initialising",

        init() {
            if (this.selectedTicker !== "") {
                this.selectTicker(this.selectedTicker);
            } else {
                this.status = "Ticker not selected";
            }

            fetch("/dividends")
                .then(async resp => {
                    return resp.ok ? resp.json() : Promise.reject(await resp.text());
                })
                .then(json => {
                    this.sec = json;
                    this.prefix = "";
                })
                .catch(err => {
                    this.sec = [];
                    this.prefix = "";
                    this.status = err;
                });
        },

        withPrefix(ticker) {
            const prefix = this.prefix.toUpperCase();

            return  prefix && ticker.startsWith(prefix);
        },

        selectTicker(ticker) {
            fetch(`/dividends/${ticker}`)
                .then(async resp => {
                    return resp.ok ? resp.json() : Promise.reject(await resp.text());
                })
                .then(json => {
                    this.selectedTicker = ticker;

                    this.dividends = json.map( row => {
                        const {date, ...rest} = row;
                        rest.date = new Date(date + ".000Z");

                        return rest;
                    });

                    this.newDate = this.formatDate(new Date());
                    this.newValue = 0.0;
                    this.newCurrency = "RUR";

                    if (this.dividends.length !== 0) {
                        const last = this.dividends[this.dividends.length - 1];

                        this.newDate = this.formatDate(last.date);
                        this.newValue = last.dividend;
                        this.newCurrency = last.currency;
                    }

                    this.status = "Not edited";
                })
                .catch(err => {
                    this.dividends = [];
                    this.status = err;
                });
        },

        get showButton() {
            return  ![
                "Initialising",
                "Ticker not selected",
                "Not edited",
                "Saved successfully",
            ].includes(this.status);
        },

        get showDividends() {
            return this.newCurrency !== "";
        },

        get count() {
            return this.dividends
                .filter(div => (div.status !== "missed")).length;
        },

        formatDate(date) {
            return  date.toISOString().slice(0, 10);
        },

        statusToBtn(status) {
            switch (status) {
                case "extra":
                    return "Remove";
                case "missed":
                    return "Accept";
                default:
                    return "";
            }
        },

        manageStatus(index) {
            switch (this.dividends[index].status) {
                case "extra":
                    this.dividends.splice(index, 1);
                    this.status = "Edited";

                    break;
                case "missed":
                    this.dividends[index].status = "ok";
                    this.status = "Edited";

                    break;
            }
        },

        add() {
            this.dividends.push({
                date: new Date(this.newDate),
                dividend: parseFloat(this.newValue),
                currency: this.newCurrency,
                status: "extra",
            });

            this.dividends.sort((a, b) => a.date - b.date);

            this.status = "Edited";
        },

        async save() {
            this.status = "Saving";

            const div = this.dividends
                .filter(div => (div.status !== "missed"))
                .map(div => {
                    const {status, ...rest} = div;

                    return rest;
                })

            fetch(`/dividends/${this.selectedTicker}`, {
                method: "PUT",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify(div)
            }).then( async resp => {
                this.status = resp.ok ? "Saved successfully" : await resp.text();
            }).catch(err => {
                this.status = err;
            });
        },
    };
};