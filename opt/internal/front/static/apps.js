window.pagesApp = function () {
    "use strict";

    return {
        selectedSection: this.$persist("Tickers").as("page_selected"),
        sections: ["Tickers", "Dividends", "Accounts", "Portfolio", "Metrics", "Optimizer", "Reports"],

        isSelectedSection(section) {
            return section === this.selectedSection;
        },
        selectSection(section) {
            this.selectedSection = section;
        }
    };
};

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
            this.selectedTicker = ticker;

            fetch(`/dividends/${ticker}`)
                .then(async resp => {
                    return resp.ok ? resp.json() : Promise.reject(await resp.text());
                })
                .then(json => {
                    this.dividends = json.map( row => {
                        const {date, ...rest} = row;
                        rest.date = new Date(date);

                        return rest;
                    });

                    this.newDate = this.formatDate(new Date());
                    this.newValue = 0.0;
                    this.newCurrency = "RUR";

                    if (this.dividends.length !== 0) {
                        const last = this.dividends[this.dividends.length - 1];

                        this.newDate = this.formatDate(last.date);
                        this.newValue = last.value;
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
                value: parseFloat(this.newValue),
                currency: this.newCurrency,
                status: "extra",
            });

            this.dividends.sort((a, b) => a.date - b.date);

            this.status = "Edited";
        },

        async save() {
            this.status = "Saving";

            const div = {
                "ticker": this.selectedTicker,
                "dividends": this.dividends
                    .filter(div => (div.status !== "missed"))
                    .map(div => {
                        const {status, ...rest} = div;

                        return rest;
                    }),
            };

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

