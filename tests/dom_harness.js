"use strict";
// Numeric DOM/layout doubles, NOT WebKit, a browser or captured Calcpad output.
// The deliberately overflowing dvr/sup/sub boxes exercise measured geometry.
const fs = require("fs");
const vm = require("vm");
const input = JSON.parse(fs.readFileSync(0, "utf8"));
let fontScale = 1, scale = 1, mutations = 0;
const frames = [];
const observers = [];

class Events {
    constructor() { this.listeners = new Map(); }
    addEventListener(type, fn, options = {}) {
        const list = this.listeners.get(type) || [];
        list.push({fn, once: Boolean(options.once)});
        this.listeners.set(type, list);
    }
    dispatch(type) {
        const list = this.listeners.get(type) || [];
        this.listeners.set(type, list.filter(item => !item.once));
        list.forEach(item => item.fn());
    }
    listenerCount() { return [...this.listeners.values()].reduce((n, list) => n + list.length, 0); }
}
class Text {
    constructor(text) { this.nodeType = 3; this.textContent = text; this.parentNode = null; }
    get nextSibling() {
        const siblings = this.parentNode.childNodes;
        return siblings[siblings.indexOf(this) + 1] || null;
    }
    get parentElement() { return this.parentNode; }
    toJSON() { return this.textContent; }
}
class Element extends Events {
    constructor(tag, attrs = {}, namespace = "http://www.w3.org/1999/xhtml") {
        super();
        this.nodeType = 1;
        this.tagName = tag.toUpperCase();
        this.namespaceURI = namespace;
        this.attrs = {...attrs};
        this.childNodes = [];
        this.parentNode = null;
        this.style = new Proxy({}, {set(object, key, value) {
            if (object[key] !== value) ++mutations;
            object[key] = value;
            return true;
        }});
    }
    get parentElement() { return this.parentNode; }
    get isConnected() { return this === root || Boolean(this.parentNode && this.parentNode.isConnected); }
    get isContentEditable() { return this.attrs.contenteditable === "true"; }
    get children() { return this.childNodes.filter(node => node.nodeType === 1); }
    get firstChild() { return this.childNodes[0] || null; }
    get nextSibling() {
        const siblings = this.parentNode.childNodes;
        return siblings[siblings.indexOf(this) + 1] || null;
    }
    get nextElementSibling() {
        let node = this.nextSibling;
        while (node && node.nodeType !== 1) node = node.nextSibling;
        return node;
    }
    get textContent() { return this.childNodes.map(node => node.textContent).join(""); }
    get classList() {
        const element = this;
        const names = () => (element.attrs.class || "").split(/\s+/).filter(Boolean);
        return {
            contains(name) { return names().includes(name); },
            add(name) {
                const value = [...new Set([...names(), name])].join(" ");
                if (value !== element.attrs.class) ++mutations;
                element.attrs.class = value;
            },
            [Symbol.iterator]() { return names()[Symbol.iterator](); }
        };
    }
    setAttribute(name, value) {
        value = String(value);
        if (this.attrs[name] !== value) ++mutations;
        this.attrs[name] = value;
    }
    getAttribute(name) { return this.attrs[name] === undefined ? null : this.attrs[name]; }
    appendChild(node) { return this.insertBefore(node, null); }
    insertBefore(node, reference) {
        if (node === reference) return node;
        if (node.parentNode) {
            const siblings = node.parentNode.childNodes;
            siblings.splice(siblings.indexOf(node), 1);
        }
        const index = reference === null ? this.childNodes.length : this.childNodes.indexOf(reference);
        if (index < 0) throw new Error("Invalid insertBefore reference");
        this.childNodes.splice(index, 0, node);
        node.parentNode = this;
        ++mutations;
        return node;
    }
    querySelectorAll(selector) {
        const result = [];
        function visit(element) {
            element.children.forEach(child => {
                if (selector === "*" || (selector === "span" && child.tagName === "SPAN")) result.push(child);
                else if (selector !== "*" && selector !== "span") throw new Error("Unexpected selector: " + selector);
                visit(child);
            });
        }
        visit(this);
        return result;
    }
    getBoundingClientRect() { return rectangle(this); }
    toJSON() {
        return {tag: this.tagName.toLowerCase(), attrs: this.attrs, style: {...this.style}, children: this.childNodes};
    }
}
const cls = (node, name) => node.nodeType === 1 && node.classList.contains(name);
const num = value => parseFloat(value) || 0;
const rect = (left, top, width, height) => ({left, top, right: left + width, bottom: top + height, width, height});
function font(node) {
    if (!node || !node.parentNode) return 16 * fontScale;
    const parent = font(node.parentNode);
    if (cls(node, "cp-preview-root-index")) return parent * .65;
    if (node.tagName === "SUP" || node.tagName === "SUB") return parent * .7;
    if (cls(node, "low")) return parent * .7;
    return parent;
}
function padding(node) {
    const em = font(node);
    const p = {left: 0, right: 0, top: 0, bottom: 0};
    if (cls(node, "cp-preview-root")) { p.left = em * .85; p.right = em * .12; }
    if (node.attrs && node.attrs["data-padding"]) {
        const [top, right, bottom, left] = node.attrs["data-padding"].split(",").map(Number);
        Object.assign(p, {top, right, bottom, left});
    }
    for (const [name, key] of [["paddingLeft", "left"], ["paddingRight", "right"],
        ["paddingTop", "top"], ["paddingBottom", "bottom"]]) {
        if (node.style && node.style[name] !== undefined) p[key] = num(node.style[name]);
    }
    return p;
}
function offset(node) {
    let x = node.attrs ? num(node.attrs["data-shift-x"]) : 0;
    let y = node.attrs ? num(node.attrs["data-shift-y"]) : 0;
    if (cls(node, "dvr")) y -= 4; // CSS top:-3pt, not part of the flow box.
    if (node.tagName === "SUP" && !cls(node, "cp-preview-root-index")) y -= font(node.parentNode) * .55;
    if (node.tagName === "SUB") y += font(node.parentNode) * .30;
    if (cls(node, "low")) y += font(node) * 1.2;
    return {x, y};
}
function measure(node) {
    const em = font(node);
    if (node.nodeType === 3) {
        const text = node.textContent.trim();
        return {width: text.length * em * .5, height: text ? em * 1.1 : 0, positions: new Map()};
    }
    if (cls(node, "cp-preview-root-marker")) return {width: 0, height: 0, positions: new Map()};
    if (node.namespaceURI === "http://www.w3.org/2000/svg") {
        return {width: num(node.style.width), height: num(node.style.height), positions: new Map()};
    }
    const p = padding(node);
    const positions = new Map();
    let width = 0, height = em * 1.2;
    const flow = node.childNodes.filter(child => !cls(child, "cp-preview-root-sign") &&
        !cls(child, "cp-preview-root-index") && !cls(child, "cp-preview-root-marker"));
    if (["dvc", "dvr", "dvs"].some(name => cls(node, name))) {
        const numerator = flow.find(child => cls(child, "dvl"));
        const rest = flow.filter(child => child !== numerator);
        const upper = numerator ? measure(numerator) : {width: 0, height: 0};
        const sizes = rest.map(measure);
        const lowerWidth = sizes.reduce((sum, item) => sum + item.width, 0);
        width = Math.max(upper.width, lowerWidth) + 16 / 3;
        if (numerator) positions.set(numerator, {x: (width - upper.width) / 2, y: 0});
        let x = (width - lowerWidth) / 2;
        rest.forEach((child, i) => {
            positions.set(child, {x, y: upper.height + 3});
            x += sizes[i].width;
        });
        height = upper.height + 3 + Math.max(0, ...sizes.map(item => item.height));
    } else {
        flow.forEach(child => {
            const size = measure(child);
            positions.set(child, {x: width + p.left, y: p.top});
            width += size.width;
            if (child.tagName !== "SUP" && child.tagName !== "SUB") height = Math.max(height, size.height);
        });
    }
    node.children.forEach(child => {
        if (cls(child, "cp-preview-root-sign")) positions.set(child, {x: 0, y: 0});
        if (cls(child, "cp-preview-root-index")) positions.set(child, {x: font(child) * .04, y: 0});
        if (cls(child, "cp-preview-root-marker")) positions.set(child, {x: 0, y: 0});
    });
    return {width: width + p.left + p.right, height: height + p.top + p.bottom,
        contentWidth: width, contentHeight: height, positions};
}
function origin(node) {
    if (!node.parentNode) return {x: 37, y: 21};
    const base = origin(node.parentNode);
    const position = measure(node.parentNode).positions.get(node) || {x: 0, y: 0};
    const shift = offset(node);
    return {x: base.x + position.x + shift.x, y: base.y + position.y + shift.y};
}
function rectangle(node) {
    for (let ancestor = node; ancestor; ancestor = ancestor.parentNode) {
        if (cls(ancestor, "cp-preview-root-marker")) return rect(0, 0, 0, 0);
    }
    const point = origin(node), size = measure(node);
    return rect(point.x * scale, point.y * scale, size.width * scale, size.height * scale);
}
function hydrate(data) {
    if (typeof data === "string") return new Text(data);
    const element = new Element(data.tag, data.attrs);
    data.children.forEach(child => element.appendChild(hydrate(child)));
    return element;
}
const root = hydrate(input.tree);
const document = new Events();
const html = new Element("html");
html.childNodes = [root];
root.parentNode = html;
document.documentElement = html;
document.createElement = tag => new Element(tag);
document.createElementNS = (ns, tag) => new Element(tag, {}, ns);
document.querySelectorAll = selector => {
    if (selector === "span") return html.querySelectorAll("span");
    if (selector !== ".eq span") throw new Error("Unexpected document selector: " + selector);
    return html.querySelectorAll("span").filter(node => {
        for (let el = node.parentElement; el; el = el.parentElement) if (cls(el, "eq")) return true;
        return false;
    });
};
document.createRange = () => {
    let selected;
    return {
        selectNodeContents(node) { selected = node; },
        getClientRects() {
            const result = [];
            function visit(node) {
                node.childNodes.forEach(child => {
                    result.push(rectangle(child));
                    if (child.nodeType === 1) visit(child);
                });
            }
            visit(selected);
            return result;
        }
    };
};
document.fonts = new Events();
let fontReady;
document.fonts.ready = {then(fn) { fontReady = fn; }};
const window = new Events();
window.visualViewport = new Events();
window.getComputedStyle = node => {
    const p = padding(node), size = measure(node);
    return {fontSize: font(node) + "px", width: size.contentWidth + "px", height: size.contentHeight + "px",
        paddingLeft: p.left + "px", paddingRight: p.right + "px",
        paddingTop: p.top + "px", paddingBottom: p.bottom + "px", boxSizing: "content-box"};
};
window.requestAnimationFrame = fn => { frames.push(fn); return frames.length; };
window.setTimeout = fn => { frames.push(fn); return frames.length; };
window.ResizeObserver = class {
    constructor(callback) { this.callback = callback; this.observed = new Set(); observers.push(this); }
    observe(node) { this.observed.add(node); }
    unobserve(node) { this.observed.delete(node); }
};
function flush() {
    let count = 0;
    while (frames.length) {
        if (++count > 10) throw new Error("Redraw loop in scheduled callbacks");
        frames.shift()();
    }
    return count;
}
function find(name) { return html.querySelectorAll("*").filter(node => cls(node, name)); }
function localBox(node, outer) {
    const a = rectangle(node), b = rectangle(outer);
    return {left: (a.left - b.left) / scale, right: (a.right - b.left) / scale,
        top: (a.top - b.top) / scale, bottom: (a.bottom - b.top) / scale};
}
function snapshot() {
    return {tree: root, diagnostics: {...html.attrs}, roots: find("cp-preview-root").map(outer => {
        const radicand = outer.children.find(child => cls(child, "cp-preview-radicand"));
        const svg = outer.children.find(child => cls(child, "cp-preview-root-sign"));
        return {box: rectangle(outer), font: font(outer), padding: padding(outer),
            radicand: localBox(radicand, outer),
            descendants: radicand.querySelectorAll("*").filter(node => node.namespaceURI !== "http://www.w3.org/2000/svg" &&
                !cls(node, "cp-preview-root-marker")).map(node => ({tag: node.tagName, classes: node.attrs.class || "", box: localBox(node, outer)})),
            svg: svg.toJSON(), scale};
    })};
}
const textBefore = root.textContent;
const context = vm.createContext({document, window, console});
// Allow shared CI hosts headroom; this does not alter production JavaScript.
vm.runInContext(input.script, context, {timeout: 5000});
flush();
const initial = JSON.parse(JSON.stringify(snapshot()));
const beforeRepeat = JSON.stringify(root);
const beforeListeners = window.listenerCount() + document.listenerCount() + document.fonts.listenerCount() + window.visualViewport.listenerCount();
const beforeRepeatMutations = mutations;
vm.runInContext(input.script, context, {timeout: 5000});
flush();
const idempotent = beforeRepeat === JSON.stringify(root);
const repeatWrites = mutations - beforeRepeatMutations;
const afterListeners = window.listenerCount() + document.listenerCount() + document.fonts.listenerCount() + window.visualViewport.listenerCount();
const results = [];
for (const event of input.events || []) {
    if (event.fontScale !== undefined) fontScale = event.fontScale;
    if (event.scale !== undefined) scale = event.scale;
    const before = mutations;
    if (event.type === "DOMContentLoaded") document.dispatch(event.type);
    else if (event.type === "fontready") { if (fontReady) fontReady(); }
    else if (event.type === "loadingdone") document.fonts.dispatch(event.type);
    else if (event.type === "observer") observers.forEach(observer => observer.callback([]));
    else if (event.type === "visualresize") window.visualViewport.dispatch("resize");
    else if (event.type === "burst") {
        window.dispatch("resize"); window.visualViewport.dispatch("resize");
        observers.forEach(observer => observer.callback([]));
    } else window.dispatch(event.type);
    const queued = frames.length;
    const frameCount = flush();
    results.push({...JSON.parse(JSON.stringify(snapshot())), type: event.type,
        writes: mutations - before, queued, frameCount});
}
process.stdout.write(JSON.stringify({initial, events: results, textBefore, textAfter: root.textContent,
    idempotent, repeatWrites, listenerStable: beforeListeners === afterListeners,
    observerCount: observers.length}));
