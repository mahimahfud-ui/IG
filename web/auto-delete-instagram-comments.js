/**
 * Instagram Bulk Comments Deletion Script
 *
 * Purpose:
 * Automates the selection and deletion of comments using Instagram’s
 * current Bloks-based UI and the confirmation React modal.
 *
 * Execution:
 * 1. Open Instagram in a desktop browser.
 * 2. Navigate to the comments activity page:
 *    https://www.instagram.com/your_activity/interactions/comments
 * 3. Open your browser developer console (preferable Chrome).
 * 4. Paste this script and execute it.
 *
 * Notes:
 * - Deletions are irreversible.
 * - Instagram allows selecting up to 100 comments per action, but
 *   smaller batches are more reliable.
 * - Recommended batch size is 5–50 to reduce the risk of temporary
 *   action limits or account restrictions.
 *
 * Configuration:
 * - Modify the MAX constant in the script to control how many comments
 *   are deleted per execution.
 * - Adjust delays (CYCLE_DELAY, SELECT_DELAY, ICON_DELAY, SELECTION_SETTLE_DELAY, DELETE_DELAY)
 *
 *
 * Troubleshooting:
 * - If pasting is blocked, type `allow pasting` in the console and
 *   press Enter, then paste the script again.
 *
 * - To stop repeated execution, set `window.__STOP_IG_BULK_DELETE__ = true` in the console.
 *
 * Disclaimer:
 * Use at your own risk. The author is not responsible for any account restrictions,
 * issues or data loss resulting from the use of this script.
 */

(async function instagramBulkDelete() {
  window.__STOP_IG_BULK_DELETE__ = false;

  /**
   * Runtime configuration.
   * Keep MAX low for reliability.
   */
  const MAX = 10;
  const CYCLE_DELAY = 20000;
  const SELECT_DELAY = 1200;
  const ICON_DELAY = 700;
  const SELECTION_SETTLE_DELAY = 5000;
  const DELETE_DELAY = 1500;
  const ERROR_POPUP_CHECK_INTERVAL = 500;
  const ERROR_POPUP_WAIT = 8000;

  let errorPopupDismissed = false;

  /**
   * Utility: async sleep helper.
   */
  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

  /**
   * Dispatches pointer events to simulate a real user click.
   * Required for Bloks UI elements which ignore .click().
   */
  function realClick(element) {
    if (!element) return;

    element.scrollIntoView({ block: "center", inline: "nearest" });
    const rect = element.getBoundingClientRect();
    const clientX = rect.left + rect.width / 2;
    const clientY = rect.top + rect.height / 2;

    if (typeof PointerEvent === "function") {
      ["pointerover", "pointerenter", "pointerdown", "pointerup"].forEach((eventType) => {
        element.dispatchEvent(
          new PointerEvent(eventType, {
            view: window,
            bubbles: true,
            cancelable: true,
            pointerId: 1,
            pointerType: "mouse",
            isPrimary: true,
            clientX,
            clientY,
          }),
        );
      });
    }

    ["mouseover", "mouseenter", "mousedown", "mouseup", "click"].forEach((eventType) => {
      element.dispatchEvent(
        new MouseEvent(eventType, {
          view: window,
          bubbles: true,
          cancelable: true,
          buttons: 1,
          clientX,
          clientY,
        }),
      );
    });

    if (typeof element.click === "function") {
      element.click();
    }
  }

  function getElementText(el) {
    return (el?.innerText ?? el?.textContent ?? "")
      .replace(/\s+/g, " ")
      .trim();
  }

  /**
   * Locates the "Select" control that enables multi-selection mode.
   * Supports both the older Bloks structure and newer Instagram markup.
   */
  function findSelectButton() {
    const candidates = [
      ...document.querySelectorAll(
        'button, [role="button"], [aria-label], div, span',
      ),
    ];

    const modernMatch = candidates.find((el) => {
      const text = getElementText(el);
      const ariaLabel = (el.getAttribute("aria-label") || "").trim();
      return text === "Select" || ariaLabel === "Select";
    });

    if (modernMatch) return modernMatch;

    return [
      ...document.querySelectorAll(
        'div[data-bloks-name="bk.components.Flexbox"]',
      ),
    ].find((el) => getElementText(el) === "Select");
  }

  /**
   * Activates comment selection mode.
   */
  async function activateSelectMode() {
    const selectBtn = findSelectButton();
    if (!selectBtn) {
      throw new Error("Select control not found");
    }

    realClick(selectBtn);
    await sleep(SELECT_DELAY);
  }

  /**
   * Retrieves selectable comment icons (unchecked radio buttons).
   * Supports both the older Bloks checkboxes and the newer data-testid / mask-image markup.
   */
  function getSelectableIcons() {
    const candidates = [
      ...document.querySelectorAll(
        '[data-testid="bulk_action_checkbox"] [role="button"], [aria-label="Toggle checkbox"], [role="button"][aria-label="Toggle checkbox"], div[style*="circle__outline"], div[style*="mask-image"][style*="circle__outline"]',
      ),
    ];

    return candidates.filter((el) => {
      const style = (el.getAttribute("style") || "").toLowerCase();
      const ariaLabel = (el.getAttribute("aria-label") || "").trim();
      const isToggleCheckbox = ariaLabel === "Toggle checkbox";
      const isOutlineIcon = style.includes("circle__outline") || style.includes("circle__outline__24");

      return isToggleCheckbox || isOutlineIcon || el.closest('[data-testid="bulk_action_checkbox"]');
    });
  }

  /**
   * Selects up to `max` comments.
   */
  async function selectComments(max) {
    const icons = getSelectableIcons();
    if (!icons.length) {
      return 0;
    }

    let selected = 0;

    for (const icon of icons) {
      if (selected >= max) break;

      icon.scrollIntoView({ behavior: "smooth", block: "center" });
      await sleep(400);

      const button = icon.closest('[role="button"]');
      if (!button) continue;

      realClick(button);
      selected++;
      await sleep(ICON_DELAY);
    }

    return selected;
  }

  /**
   * Locates the Delete control in the selection bar.
   * Supports both the older Bloks text nodes and the newer React/button markup.
   */
  function findBloksDeleteButton() {
    const candidates = [
      ...document.querySelectorAll(
        '[role="button"][aria-label="Delete"], button[aria-label="Delete"], [aria-label="Delete"]',
      ),
    ];

    const clickable = candidates
      .filter((el) => {
        const text = getElementText(el);
        const ariaLabel = (el.getAttribute("aria-label") || "").trim();
        const style = (el.getAttribute("style") || "").toLowerCase();

        const isDelete = ariaLabel === "Delete" || text === "Delete" || text.includes("Delete");
        const visible = !style.includes("display: none") && !style.includes("visibility: hidden");
        const interactive = style.includes("pointer-events: auto") || el.getAttribute("role") === "button";

        return isDelete && visible && interactive;
      })
      .sort((a, b) => {
        const aDepth = a.querySelectorAll('[role="button"][aria-label="Delete"]').length;
        const bDepth = b.querySelectorAll('[role="button"][aria-label="Delete"]').length;
        return aDepth - bDepth;
      });

    if (clickable.length) {
      return clickable[0];
    }

    const spanDelete = [...document.querySelectorAll("span")].find(
      (el) => getElementText(el) === "Delete",
    );

    if (spanDelete) {
      return spanDelete.closest('[role="button"][aria-label="Delete"], button, [role="button"]') || spanDelete;
    }

    return null;
  }

  /**
   * Triggers the initial delete action in the selection UI.
   */
  async function clickBloksDelete() {
    console.log("Waiting for Instagram to finish registering the selected comments...");
    await sleep(SELECTION_SETTLE_DELAY);

    const deleteBtn = findBloksDeleteButton();
    if (!deleteBtn) {
      throw new Error("Bloks Delete control not found");
    }

    realClick(deleteBtn);
  }

  /**
   * Locates the confirmation action in the popup dialog.
   * Instagram is rendering the confirmation as a visible text node and may not use a normal button.
   */
  function findModalDeleteButton() {
    const buttonMatch = [...document.querySelectorAll("button")].find(
      (btn) => getElementText(btn) === "Delete",
    );

    if (buttonMatch) return buttonMatch;

    const candidates = [
      ...document.querySelectorAll(
        "button, [role='button'], [role=\"button\"], [aria-label='Delete'], [aria-label=\"Delete\"], div, span",
      ),
    ];

    return candidates.find((el) => {
      const text = getElementText(el);
      const ariaLabel = (el.getAttribute("aria-label") || "").trim();
      const style = (el.getAttribute("style") || "").toLowerCase();
      const className = (el.className || "").toString();

      const isDelete = text === "Delete" || ariaLabel === "Delete";
      const isVisible = !style.includes("display: none") && !style.includes("visibility: hidden");
      const isDialogLike = className.includes("_ap3a") || className.includes("_aacp") || className.includes("_aacw");

      return isDelete && isVisible && (isDialogLike || el.getAttribute("role") === "button" || el.tagName === "BUTTON");
    });
  }

  function dismissPopupIfPresent() {
    const dialogs = [
      ...document.querySelectorAll('[role="dialog"], [aria-modal="true"]'),
    ];

    const errorDialog = dialogs.find((dialog) => {
      const text = getElementText(dialog);
      return text.includes("Something went wrong") || text.includes("Try deleting it again");
    });

    if (!errorDialog) {
      return false;
    }

    const searchRoot = errorDialog;
    const okText = [...searchRoot.querySelectorAll("button, [role='button'], div, span")]
      .find((el) => getElementText(el).trim() === "OK");
    const okBtn = okText?.closest("button, [role='button']") || okText;

    if (okBtn) {
      errorPopupDismissed = true;
      okBtn.focus?.();
      realClick(okBtn);
      if (okText && okText !== okBtn) {
        realClick(okText);
      }
      console.log("Dismissed Instagram popup: OK");
      return true;
    }

    return false;
  }

  async function waitForErrorPopupAndDismiss(timeout = ERROR_POPUP_WAIT) {
    const startedAt = Date.now();

    while (Date.now() - startedAt < timeout) {
      if (dismissPopupIfPresent()) {
        await sleep(1000);
        return true;
      }

      await sleep(ERROR_POPUP_CHECK_INTERVAL);
    }

    return false;
  }

  const popupMonitor = setInterval(() => {
    if (window.__STOP_IG_BULK_DELETE__) {
      clearInterval(popupMonitor);
      return;
    }

    dismissPopupIfPresent();
  }, ERROR_POPUP_CHECK_INTERVAL);

  /**
   * Confirms deletion in the modal dialog.
   */
  async function confirmFinalDelete() {
    await sleep(DELETE_DELAY);

    const modalDeleteBtn = findModalDeleteButton();
    if (!modalDeleteBtn) {
      throw new Error("Final confirmation button not found");
    }

    modalDeleteBtn.focus();
    await sleep(100);
    realClick(modalDeleteBtn);

    return waitForErrorPopupAndDismiss();
  }

  async function dismissPopupAfterError() {
    return waitForErrorPopupAndDismiss();
  }

  /**
   * Main execution loop.
   */
  let cycle = 1;

  while (!window.__STOP_IG_BULK_DELETE__) {
    try {
      await activateSelectMode();
      const deletedCount = await selectComments(MAX);

      if (!deletedCount) {
        console.log("No comments left to delete");
        break;
      }

      await clickBloksDelete();
      errorPopupDismissed = false;
      const deleteProblemShown = await confirmFinalDelete();

      if (deleteProblemShown || errorPopupDismissed) {
        console.warn("Instagram reported a delete problem. Dismissed it and continuing...");
        await sleep(CYCLE_DELAY);
        continue;
      }

      console.log(`Cycle ${cycle}: deleted ${deletedCount} comments`);
      cycle++;

      await sleep(3500);
      console.log("Waiting for Instagram to finish deleting and refresh the list...");
      await sleep(CYCLE_DELAY - 3500);
    } catch (error) {
      if (await dismissPopupAfterError()) {
        console.warn("Instagram reported a delete problem. Continuing with the next cycle...");
        await sleep(CYCLE_DELAY);
        continue;
      }

      console.warn("Execution stopped:", error.message);
      break;
    }
  }
})();
