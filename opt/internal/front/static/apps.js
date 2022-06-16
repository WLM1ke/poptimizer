window.pagesApp = function () {
    "use strict";

    return {
        selected: this.$persist("Tickers").as("page_selected"),
        sections: ["Tickers", "Dividends", "Accounts", "Portfolio", "Metrics", "Optimizer", "Reports"],

        isSelected(section) {
            return section === this.selected;
        },
        select(section) {
            this.selected = section;
            this.selected_saved = section;
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
                .then(async resp => resp.ok? resp.json() : Promise.reject(await resp.text()))
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
                if (resp.ok) {
                    this.status = "Saved successfully";

                    return;
                }

                return Promise.reject(await resp.text());
            }).catch(err => {
                this.status = err;
            });
        },
    };
};
