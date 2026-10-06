/* Moderation page (admin/spam_page.html), moved out of the template for the CSP. */
    //to select all visible elements in a table
    function toggle(source, name) {
        var checkboxes = Array.from(document.querySelectorAll(`input[name=${name}]`)).filter(checkbox => isVisible(checkbox));
        for (var i = 0; i < checkboxes.length; i++) {
            if (checkboxes[i] != source)
                checkboxes[i].checked = source.checked;
        }
    }

    // check if an element is visible, used in toggle to select all visible elements
    function isVisible(element){
        while(element){
            if (getComputedStyle(element).display === "none") return false;
                element = element.parentElement;
        }
        return true;
    }

    // Search bar before each table
    function searchBar(type, input) {
    // Assign values to the variables depending on the type of element
    var filter, table, tr, td, i, txtValue;

    if (type == "user"){
        filter = input.value.toUpperCase();
        table = document.getElementById("userTable");
        tr = table.getElementsByTagName("tr");
    } else if (type == "org"){
        filter = input.value.toUpperCase();
        table = document.getElementById("orgTable");
        tr = table.getElementsByTagName("tr");
    } else if (type == "mod_petition"){
        filter = input.value.toUpperCase();
        table = document.getElementById("modPetitionTable");
        tr = table.getElementsByTagName("tr");
    } else if (type == "mon_petition"){
        filter = input.value.toUpperCase();
        table = document.getElementById("monPetitionTable");
        tr = table.getElementsByTagName("tr");
    } else if (type == "rep_petition"){
        filter = input.value.toUpperCase();
        table = document.getElementById("repPetitionTable");
        tr = table.getElementsByTagName("tr");
    }

    // Loop through all table rows, and hide those who don't match the search query
    for (i = 0; i < tr.length; i++) {
        td = tr[i].getElementsByTagName("td")[1];
        if (td) {
            txtValue = td.textContent || td.innerText;
        if (txtValue.toUpperCase().indexOf(filter) > -1) {
            tr[i].style.display = "";
        } else {
            tr[i].style.display = "none";
        }
        }
    }
    }

    // sort tables by clicking on a column
    function sortTable(table_id, column) {
        const table = document.getElementById(table_id);
        let switching = true;

        while (switching) {
            switching = false;
            let rows = table.tBodies[0].querySelectorAll(":scope > tr");

            for (let i = 0; i < rows.length - 1; i++) {
                let x = rows[i].cells[column];
                let y = rows[i + 1].cells[column];

            if (x && y) {
                let valX = x.textContent.trim();
                let valY = y.textContent.trim();

                if (Number(valX) < Number(valY)) {
                    rows[i].parentNode.insertBefore(rows[i + 1], rows[i]);
                    switching = true;
                    break;
                }
            }
            }
        }
        const rowIds = Array.from(table.tBodies[0].rows).map(r => r.id);
        localStorage.setItem(`table_order_${table_id}`, JSON.stringify(rowIds));
    }

    function showVariables() {
        var x = document.getElementById("mod_variables");
        if (x.style.display === "none") {
            x.style.display = "block";
        } else {
            x.style.display = "none";
        }
        localStorage.setItem('mod_variables_display', x.style.display);
    }

    // Sortable headers: keyboard-accessible buttons, the sorted column is announced with aria-sort
    document.addEventListener('click', (event) => {
        const button = event.target.closest('button[data-sort-table]');
        if (!button) return;
        const tableId = button.dataset.sortTable;
        sortTable(tableId, Number(button.dataset.sortCol));
        document.querySelectorAll(`#${tableId} th[aria-sort]`).forEach(th => th.removeAttribute('aria-sort'));
        button.closest('th').setAttribute('aria-sort', 'descending');
    });

    document.addEventListener('DOMContentLoaded', () => {
        const x = document.getElementById('mod_variables');
        const saved = localStorage.getItem('mod_variables_display');
        if (saved) x.style.display = saved; // 'block' ou 'none'
    });


    // Listeners replacing the inline event handlers (Content-Security-Policy)
    document.addEventListener('keyup', (event) => {
        const input = event.target.closest('input[data-search-type]');
        if (input) searchBar(input.dataset.searchType, input);
    });
    document.addEventListener('click', (event) => {
        const selectAll = event.target.closest('input[data-select-all]');
        if (selectAll) toggle(selectAll, selectAll.dataset.selectAll);
        if (event.target.closest('[data-toggle-variables]')) showVariables();
    });
