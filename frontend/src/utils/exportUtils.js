import html2canvas from "html2canvas";
import { jsPDF } from "jspdf";
import api from "../services/api";

/**
 * Captures an exact visual replica of any DOM container on the page
 * and exports it as a multi-page A4 PDF document.
 * 
 * @param {string} elementId - HTML id or selector of the page container
 * @param {string} filename - Output filename (e.g. 'Project_Analysis_Report.pdf')
 * @returns {Promise<void>}
 */
export const exportPageToPDF = async (elementId, filename = "EventPath_Page_Report.pdf") => {
  const element = typeof elementId === "string" 
    ? document.getElementById(elementId) || document.querySelector(elementId)
    : elementId;

  if (!element) {
    throw new Error(`Element with id or selector "${elementId}" not found.`);
  }

  // Scroll to top to ensure complete canvas capture
  window.scrollTo(0, 0);

  // High DPI canvas options
  const canvas = await html2canvas(element, {
    scale: 2, // 2x resolution for high sharpness
    useCORS: true,
    allowTaint: true,
    logging: false,
    backgroundColor: getComputedStyle(document.documentElement)
      .getPropertyValue("--bg-primary") || "#f8fafc",
    windowWidth: element.scrollWidth,
    windowHeight: element.scrollHeight,
    onclone: (clonedDoc) => {
      // Ensure hidden items for print are preserved or formatted appropriately
      const clonedElement = clonedDoc.querySelector(elementId.startsWith('#') || elementId.startsWith('.') ? elementId : `#${elementId}`);
      if (clonedElement) {
        clonedElement.style.padding = "24px";
        clonedElement.style.borderRadius = "0px";
        clonedElement.style.boxShadow = "none";
      }
    }
  });

  const imgData = canvas.toDataURL("image/png");
  const pdf = new jsPDF("p", "mm", "a4");

  const pdfWidth = pdf.internal.pageSize.getWidth(); // 210mm
  const pdfHeight = pdf.internal.pageSize.getHeight(); // 297mm

  const imgWidth = pdfWidth;
  const imgHeight = (canvas.height * pdfWidth) / canvas.width;

  let heightLeft = imgHeight;
  let position = 0;

  // First page
  pdf.addImage(imgData, "PNG", 0, position, imgWidth, imgHeight, undefined, "FAST");
  heightLeft -= pdfHeight;

  // Add subsequent pages if content exceeds single A4 page
  while (heightLeft > 0) {
    position = heightLeft - imgHeight;
    pdf.addPage();
    pdf.addImage(imgData, "PNG", 0, position, imgWidth, imgHeight, undefined, "FAST");
    heightLeft -= pdfHeight;
  }

  pdf.save(filename.endsWith(".pdf") ? filename : `${filename}.pdf`);
};

/**
 * Formats a JavaScript array of objects into a CSV string and triggers a browser file download.
 * 
 * @param {Array<Object>} data - Data rows
 * @param {string} filename - Desired CSV filename
 */
export const exportDataToCSV = (data, filename = "EventPath_Export.csv") => {
  if (!data || !data.length) {
    throw new Error("No data available to export to CSV.");
  }

  const headers = Object.keys(data[0]);
  const csvRows = [];

  // Header row
  csvRows.push(headers.map((h) => `"${h.replace(/"/g, '""')}"`).join(","));

  // Data rows
  for (const row of data) {
    const values = headers.map((header) => {
      const val = row[header] === null || row[header] === undefined ? "" : String(row[header]);
      return `"${val.replace(/"/g, '""')}"`;
    });
    csvRows.push(values.join(","));
  }

  const csvString = csvRows.join("\n");
  const blob = new Blob([csvString], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);

  const link = document.createElement("a");
  link.setAttribute("href", url);
  link.setAttribute("download", filename.endsWith(".csv") ? filename : `${filename}.csv`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
};

/**
 * Downloads a generated CSV report directly from the backend API.
 * 
 * @param {string} projectId 
 * @param {string} projectName 
 */
export const downloadBackendCSV = async (projectId, projectName = "project") => {
  const response = await api.get(`/projects/${projectId}/export/csv`, {
    responseType: "blob",
  });

  const blob = new Blob([response.data], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  const safeName = projectName.toLowerCase().replace(/[^a-z0-9]/g, "_");
  link.href = url;
  link.setAttribute("download", `eventpath_${safeName}_schedule.csv`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
};

/**
 * Downloads a generated PDF report directly from the backend API.
 * 
 * @param {string} projectId 
 * @param {string} projectName 
 */
export const downloadBackendPDF = async (projectId, projectName = "project") => {
  const response = await api.get(`/projects/${projectId}/export/pdf`, {
    responseType: "blob",
  });

  const blob = new Blob([response.data], { type: "application/pdf" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  const safeName = projectName.toLowerCase().replace(/[^a-z0-9]/g, "_");
  link.href = url;
  link.setAttribute("download", `eventpath_${safeName}_report.pdf`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
};
