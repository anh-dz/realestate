function exportTableToCSV(filename) {
    const csv = [];
    const rows = document.querySelectorAll("#resultTable tr");
    for (let i = 0; i < rows.length; i++) {
        const row = [], cols = rows[i].querySelectorAll("td, th");
        // Bỏ qua cột cuối cùng (Actions)
        for (let j = 0; j < cols.length - 1; j++) { let data = cols[j].innerText.replace(/(\r\n|\n|\r)/gm, " ").replace(/,/g, ""); row.push(data); }
        csv.push(row.join(","));
    }
    downloadCSV(csv.join("\n"), filename);
}
function downloadCSV(csv, filename) {
    const csvFile = new Blob([csv], {type: "text/csv"});
    const downloadLink = document.createElement("a");
    downloadLink.download = filename;
    downloadLink.href = window.URL.createObjectURL(csvFile);
    downloadLink.style.display = "none";
    document.body.appendChild(downloadLink);
    downloadLink.click();
}