function loadModal(apiEndpoint, method = "GET") {
    return ajaxCallCsrf(
        apiEndpoint,
        {},
        method
    ).then(function(content) {
        const $modal = $(content);
        const id = $modal.attr("id");
        const $existing = id ? $("#" + id) : $();
        if ($existing.length) {
            $existing.replaceWith($modal);
        } else {
            $modal.appendTo("body");
        }
        $modal.css("display", "flex");
        let pathOpen = $modal.data("path-open");
        const currentPath = window.location.pathname;
        const fullPath = currentPath.includes(pathOpen)
            ? currentPath
            : currentPath.replace(/\/$/, "") + pathOpen;
        const pathClose = pathOpen
            ? currentPath.replace(pathOpen.replace(/^\//, ""), "")  || "/"
            : null;
        if (pathOpen) updateUrlPath(fullPath);
        bindModalCloseEvents(id, pathClose);
    });
}

function closeModal(elementId = "#modal", pathOnClose = null) {
    $(elementId).remove();
    if (pathOnClose) updateUrlPath(pathOnClose);
}

function updateUrlFromHistory() {
    if (history.state?.path) {
        history.pushState({}, '', history.state.path);
    } else {
        history.pushState({}, '', "/");
    }
}

function updateUrlPath(path) {
    console.log("Adding path to URL:", path);
    const currentPath = window.location.pathname;
    history.pushState({ path: currentPath }, '', path);
}

const _modalStack = [];

function bindModalCloseEvents(elementId, pathOnClose = null) {
    console.log("Close events path on close:", pathOnClose);
    const stackIndex = _modalStack.indexOf(elementId);
    if (stackIndex !== -1) _modalStack.splice(stackIndex, 1);
    _modalStack.push(elementId);

    function handleClose(event) {
        const isBackdropClick = event.target === $("#" + elementId)[0];
        const isCloseButton = $(event.target).closest("#" + elementId + " .close-modal-btn").length > 0;
        const isEscape = event.key === "Escape" && _modalStack[_modalStack.length - 1] === elementId;

        if (isBackdropClick || isCloseButton || isEscape) {
            const closeAll = $("#" + elementId).data("close") === "all";
            if (closeAll) {
                const stackCopy = _modalStack.slice();
                _modalStack.length = 0;
                stackCopy.forEach(function(id) {
                    $(document).off("click." + id + " keydown." + id);
                    closeModal("#" + id, id === elementId ? pathOnClose : null);
                });
            } else {
                _modalStack.splice(_modalStack.indexOf(elementId), 1);
                closeModal("#" + elementId, pathOnClose);
                $(document).off("click." + elementId + " keydown." + elementId);
            }
        }
    }

    $(document).off("click." + elementId + " keydown." + elementId)
        .on("click." + elementId + " keydown." + elementId, handleClose);
}