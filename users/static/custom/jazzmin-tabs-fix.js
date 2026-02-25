(function () {
    'use strict';

    function getTabsContainer(link) {
        return link ? link.closest('#jazzy-tabs') : null;
    }

    function getPaneSelector(link) {
        return link.getAttribute('href') || link.getAttribute('data-target');
    }

    function supportsBootstrap5(link) {
        return typeof window.bootstrap !== 'undefined' && typeof window.bootstrap.Tab !== 'undefined';
    }

    function supportsBootstrap4(link) {
        return typeof window.jQuery !== 'undefined' && typeof window.jQuery(link).tab === 'function';
    }

    function setActiveClass(link, paneSelector) {
        var tabsContainer = getTabsContainer(link);
        if (!tabsContainer) {
            return;
        }

        var allLinks = tabsContainer.querySelectorAll('.nav-link');
        for (var i = 0; i < allLinks.length; i++) {
            allLinks[i].classList.remove('active');
            allLinks[i].setAttribute('aria-selected', 'false');
            var otherPaneSelector = getPaneSelector(allLinks[i]);
            if (otherPaneSelector && otherPaneSelector.charAt(0) === '#') {
                var otherPane = document.querySelector(otherPaneSelector);
                if (otherPane) {
                    otherPane.classList.remove('active', 'show');
                }
            }
        }

        link.classList.add('active');
        link.setAttribute('aria-selected', 'true');
        var pane = document.querySelector(paneSelector);
        if (pane) {
            pane.classList.add('active', 'show');
        }
    }

    function isPaneActive(paneSelector) {
        var pane = document.querySelector(paneSelector);
        return !!(pane && pane.classList.contains('active'));
    }

    function activateTab(link, pushHash) {
        if (!link) {
            return;
        }

        var paneSelector = getPaneSelector(link);
        if (!paneSelector || paneSelector.charAt(0) !== '#') {
            return;
        }

        // Try Bootstrap native handlers first, but always fallback to manual
        // class toggling in case plugin binding is broken/incompatible.
        try {
            if (supportsBootstrap5(link)) {
                window.bootstrap.Tab.getOrCreateInstance(link).show();
            } else if (supportsBootstrap4(link)) {
                window.jQuery(link).tab('show');
            }
        } catch (e) {
            // Ignore and fallback to manual activation below.
        }

        if (!isPaneActive(paneSelector)) {
            setActiveClass(link, paneSelector);
        }

        if (pushHash) {
            if (window.history && typeof window.history.replaceState === 'function') {
                window.history.replaceState(null, '', paneSelector);
            } else {
                window.location.hash = paneSelector;
            }
        }
    }

    function bindTabsFix() {
        var links = document.querySelectorAll('#jazzy-tabs .nav-link');
        if (!links.length) {
            return;
        }

        for (var i = 0; i < links.length; i++) {
            links[i].addEventListener('click', function (event) {
                event.preventDefault();
                event.stopPropagation();
                activateTab(event.currentTarget, true);
            });
        }

        if (window.location.hash) {
            var hashLink = document.querySelector('#jazzy-tabs .nav-link[href="' + window.location.hash + '"]');
            if (hashLink) {
                activateTab(hashLink, false);
            }
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', bindTabsFix);
    } else {
        bindTabsFix();
    }
})();
