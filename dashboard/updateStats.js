// /* UPDATE THESE VALUES TO MATCH YOUR SETUP */

// const PROCESSING_STATS_API_URL = "http://acit3855lab9.eastus.cloudapp.azure.com/processing/ccc/stats"
// const ANALYZER_API_URL = {
//     stats: "http://acit3855lab9.eastus.cloudapp.azure.com/analyzer/ccc/stats",
//     clientcase: "http://acit3855lab9.eastus.cloudapp.azure.com/analyzer/ccc/clientcase?index=1",
//     survey: "http://acit3855lab9.eastus.cloudapp.azure.com/analyzer/ccc/survey?index=1"
// }

// const CONSISTENCY_CHECKS_API_URL = "http://acit3855lab9.eastus.cloudapp.azure.com/check/ccc/checks";
// const RUN_CHECKS_API_URL = "http://acit3855lab9.eastus.cloudapp.azure.com/check/ccc/update";


// // This function fetches and updates the general statistics
// const makeReq = (url, cb) => {
//     fetch(url)
//         .then(res => res.json())
//         .then((result) => {
//             console.log("Received data: ", result)
//             cb(result);
//         }).catch((error) => {
//             updateErrorMessages(error.message)
//         })
// }

// const updateCodeDiv = (result, elemId) => document.getElementById(elemId).innerText = JSON.stringify(result)

// const getLocaleDateStr = () => (new Date()).toLocaleString()

// const getStats = () => {
//     document.getElementById("last-updated-value").innerText = getLocaleDateStr()
    
//     makeReq(PROCESSING_STATS_API_URL, (result) => updateCodeDiv(result, "processing-stats"))
//     makeReq(ANALYZER_API_URL.stats, (result) => updateCodeDiv(result, "analyzer-stats"))
//     makeReq(ANALYZER_API_URL.clientcase, (result) => updateCodeDiv(result, "event-clientcase"))
//     makeReq(ANALYZER_API_URL.survey, (result) => updateCodeDiv(result, "event-survey"))
// }

// const updateErrorMessages = (message) => {
//     const id = Date.now()
//     console.log("Creation", id)
//     msg = document.createElement("div")
//     msg.id = `error-${id}`
//     msg.innerHTML = `<p>Something happened at ${getLocaleDateStr()}!</p><code>${message}</code>`
//     document.getElementById("messages").style.display = "block"
//     document.getElementById("messages").prepend(msg)
//     setTimeout(() => {
//         const elem = document.getElementById(`error-${id}`)
//         if (elem) { elem.remove() }
//     }, 7000)
// }

// const setup = () => {
//     getStats()
//     setInterval(() => getStats(), 4000) // Update every 4 seconds
// }

// document.addEventListener('DOMContentLoaded', setup)

const CONSISTENCY_CHECKS_API_URL = "http://acit3855lab9.eastus.cloudapp.azure.com/check/ccc/checks";
const RUN_CHECKS_API_URL = "http://acit3855lab9.eastus.cloudapp.azure.com/check/ccc/update";

const updateConsistencyResults = (result) => {
    document.getElementById("last-updated-checks").innerText = result.last_updated || "N/A";
    
    document.getElementById("db-counts").innerText = JSON.stringify(result.counts?.db || {});
    document.getElementById("queue-counts").innerText = JSON.stringify(result.counts?.queue || {});
    document.getElementById("processing-counts").innerText = JSON.stringify(result.counts?.processing || {});

    document.getElementById("missing-in-db").innerText = JSON.stringify(result.missing_in_db || []);
    document.getElementById("missing-in-queue").innerText = JSON.stringify(result.missing_in_queue || []);
};

const getConsistencyChecks = () => {
    fetch(CONSISTENCY_CHECKS_API_URL)
        .then(res => res.json())
        .then(updateConsistencyResults)
        .catch(error => updateErrorMessages(error.message));
};

const runConsistencyChecks = () => {
    fetch(RUN_CHECKS_API_URL, { method: "POST" })
        .then(res => res.json())
        .then((result) => {
            console.log("Check Run:", result);
            getConsistencyChecks(); // Refresh results after running the check
        })
        .catch(error => updateErrorMessages(error.message));
};

const setup = () => {
    getStats();
    getConsistencyChecks();
    setInterval(getStats, 4000);
    setInterval(getConsistencyChecks, 6000); // Refresh consistency checks every 6 seconds

    document.getElementById("run-checks-button").addEventListener("click", runConsistencyChecks);
};

document.addEventListener("DOMContentLoaded", setup);
