import{r as ve,s as O,c as X,u as Y,g as ee,d as te,n as q,e as W,f as we,o as be}from"../chunks/scheduler.-7raQLrP.js";import{t as p,d as _,S as T,i as z,x as B,y as j,j as v,f as $,k as c,a as Z,r as b,u as x,v as E,w as M,s as C,c as k,g as L,h as V,z as ue,A as I,m as fe,n as ie,o as $e,q as ne,B as Ee,p as he,b as me,C as Q,e as le,D as Me}from"../chunks/index.HDfD0nVc.js";import{k as de,w as ge}from"../chunks/singletons.dgv1qYB-.js";import{p as Ze}from"../chunks/stores.olP67FEK.js";function ae(n){return n?.length!==void 0?n:Array.from(n)}function xe(n,e){p(n,1,1,()=>{e.delete(n.key)})}function Ae(n,e,r,t,l,a,s,u,f,o,h,d){let i=n.length,m=a.length,A=i;const H={};for(;A--;)H[n[A].key]=A;const y=[],G=new Map,U=new Map,F=[];for(A=m;A--;){const S=d(l,a,A),D=r(S);let P=s.get(D);P?t&&F.push(()=>P.p(S,e)):(P=o(D,S),P.c()),G.set(D,y[A]=P),D in H&&U.set(D,Math.abs(A-H[D]))}const g=new Set,w=new Set;function N(S){_(S,1),S.m(u,h),s.set(S.key,S),h=S.first,m--}for(;i&&m;){const S=y[m-1],D=n[i-1],P=S.key,K=D.key;S===D?(h=S.first,i--,m--):G.has(K)?!s.has(P)||g.has(P)?N(S):w.has(K)?i--:U.get(P)>U.get(K)?(w.add(P),N(S)):(g.add(K),i--):(f(D,s),i--)}for(;i--;){const S=n[i];G.has(S.key)||f(S,s)}for(;m;)N(y[m-1]);return ve(F),y}const Se=!1,Ie=async()=>({}),qt=Object.freeze(Object.defineProperty({__proto__:null,load:Ie,ssr:Se},Symbol.toStringTag,{value:"Module"}));function He(n){let e,r,t;const l=n[4].default,a=X(l,n,n[3],null);return{c(){e=B("svg"),a&&a.c(),this.h()},l(s){e=j(s,"svg",{xmlns:!0,class:!0,viewBox:!0});var u=v(e);a&&a.l(u),u.forEach($),this.h()},h(){c(e,"xmlns","http://www.w3.org/2000/svg"),c(e,"class",r=n[0]+" "+n[2]),c(e,"viewBox",n[1])},m(s,u){Z(s,e,u),a&&a.m(e,null),t=!0},p(s,[u]){a&&a.p&&(!t||u&8)&&Y(a,l,s,s[3],t?te(l,s[3],u,null):ee(s[3]),null),(!t||u&5&&r!==(r=s[0]+" "+s[2]))&&c(e,"class",r),(!t||u&2)&&c(e,"viewBox",s[1])},i(s){t||(_(a,s),t=!0)},o(s){p(a,s),t=!1},d(s){s&&$(e),a&&a.d(s)}}}function Ce(n,e,r){let{$$slots:t={},$$scope:l}=e,{height:a="h-5"}=e,{viewBox:s="0 0 16 16"}=e,{fill:u="fill-current"}=e;return n.$$set=f=>{"height"in f&&r(0,a=f.height),"viewBox"in f&&r(1,s=f.viewBox),"fill"in f&&r(2,u=f.fill),"$$scope"in f&&r(3,l=f.$$scope)},[a,s,u,l,t]}class J extends T{constructor(e){super(),z(this,e,Ce,He,O,{height:0,viewBox:1,fill:2})}}function ke(n){let e,r,t,l,a,s,u,f,o,h,d;return{c(){e=B("path"),r=C(),t=B("path"),l=C(),a=B("path"),s=C(),u=B("path"),f=C(),o=B("path"),h=C(),d=B("path"),this.h()},l(i){e=j(i,"path",{fill:!0,d:!0}),v(e).forEach($),r=k(i),t=j(i,"path",{fill:!0,d:!0}),v(t).forEach($),l=k(i),a=j(i,"path",{fill:!0,d:!0}),v(a).forEach($),s=k(i),u=j(i,"path",{fill:!0,d:!0}),v(u).forEach($),f=k(i),o=j(i,"path",{fill:!0,d:!0}),v(o).forEach($),h=k(i),d=j(i,"path",{fill:!0,d:!0}),v(d).forEach($),this.h()},h(){c(e,"fill","#38bdf8"),c(e,"d","M195.804 252.9H57.096C25.613 252.9 0 227.287 0 195.804V57.096C0 25.613 25.613 0 57.096 0h138.708C227.287 0 252.9 25.613 252.9 57.096v138.708c0 31.483-25.613 57.096-57.096 57.096M57.096 15.806c-22.766 0-41.29 18.524-41.29 41.29v138.708c0 22.766 18.524 41.29 41.29 41.29h138.708c22.766 0 41.29-18.524 41.29-41.29V57.096c0-22.766-18.524-41.29-41.29-41.29H57.096"),c(t,"fill","#38bdf8"),c(t,"d","M215.013 37.265h-37.677c-3.61 0-5.418 4.363-2.865 6.916l11.706 11.706-68.316 68.317-23.923-23.923-6.412-6.412a5.555 5.555 0 0 0-7.855 0l-40.78 40.778a5.555 5.555 0 0 0 0 7.856l6.411 6.411a5.555 5.555 0 0 0 7.856 0l30.44-30.44 30.287 30.289a5.555 5.555 0 0 0 7.856 0l3.26-3.26c.168-.134.344-.253.5-.409l74.941-74.942 11.706 11.706c2.554 2.554 6.917.746 6.917-2.864V41.317a4.052 4.052 0 0 0-4.052-4.052"),c(a,"fill","#075985"),c(a,"d","m83.598 131.33-24.01 24.01a14.674 14.674 0 0 1-1.937 1.616v56.554a5.554 5.554 0 0 0 5.555 5.555h17.74a5.554 5.554 0 0 0 5.554-5.555v-79.277l-2.902-2.903"),c(u,"fill","#0369a1"),c(u,"d","M117.814 159.48c-3.912 0-7.589-1.522-10.356-4.29l-12.415-12.413v70.733a5.554 5.554 0 0 0 5.555 5.555h17.74a5.554 5.554 0 0 0 5.555-5.555v-55.36a14.568 14.568 0 0 1-6.079 1.33"),c(o,"fill","#0284c7"),c(o,"d","M132.437 151.015v62.495a5.554 5.554 0 0 0 5.555 5.555h17.74a5.554 5.554 0 0 0 5.555-5.555v-91.345l-28.85 28.85"),c(d,"fill","#0ea5e9"),c(d,"d","M169.83 113.62v99.89a5.554 5.554 0 0 0 5.554 5.555h17.74a5.554 5.554 0 0 0 5.555-5.555V84.77l-28.85 28.85")},m(i,m){Z(i,e,m),Z(i,r,m),Z(i,t,m),Z(i,l,m),Z(i,a,m),Z(i,s,m),Z(i,u,m),Z(i,f,m),Z(i,o,m),Z(i,h,m),Z(i,d,m)},p:q,d(i){i&&($(e),$(r),$(t),$(l),$(a),$(s),$(u),$(f),$(o),$(h),$(d))}}}function Le(n){let e,r;return e=new J({props:{viewBox:"0 0 256 256",height:"h-8",$$slots:{default:[ke]},$$scope:{ctx:n}}}),{c(){b(e.$$.fragment)},l(t){x(e.$$.fragment,t)},m(t,l){E(e,t,l),r=!0},p(t,[l]){const a={};l&1&&(a.$$scope={dirty:l,ctx:t}),e.$set(a)},i(t){r||(_(e.$$.fragment,t),r=!0)},o(t){p(e.$$.fragment,t),r=!1},d(t){M(e,t)}}}class Ve extends T{constructor(e){super(),z(this,e,null,Le,O,{})}}function Oe(n){let e,r,t,l,a,s="poptimizer",u;return t=new Ve({}),{c(){e=L("section"),r=L("a"),b(t.$$.fragment),l=C(),a=L("h1"),a.textContent=s,this.h()},l(f){e=V(f,"SECTION",{class:!0});var o=v(e);r=V(o,"A",{href:!0,class:!0});var h=v(r);x(t.$$.fragment,h),l=k(h),a=V(h,"H1",{class:!0,"data-svelte-h":!0}),ue(a)!=="svelte-18un3u6"&&(a.textContent=s),h.forEach($),o.forEach($),this.h()},h(){c(a,"class","font-logo text-3xl font-semibold tracking-tighter"),c(r,"href","/"),c(r,"class","flex h-full items-center gap-2"),c(e,"class","min-w-max border-r border-bg-accent bg-bg-sidebar px-4 py-2")},m(f,o){Z(f,e,o),I(e,r),E(t,r,null),I(r,l),I(r,a),u=!0},p:q,i(f){u||(_(t.$$.fragment,f),u=!0)},o(f){p(t.$$.fragment,f),u=!1},d(f){f&&$(e),M(t)}}}class Te extends T{constructor(e){super(),z(this,e,null,Oe,O,{})}}function ze(n){let e;return{c(){e=B("path"),this.h()},l(r){e=j(r,"path",{"fill-rule":!0,d:!0,"clip-rule":!0}),v(e).forEach($),this.h()},h(){c(e,"fill-rule","evenodd"),c(e,"d","M8 13.5a5.5 5.5 0 1 0 0-11 5.5 5.5 0 0 0 0 11ZM8 15A7 7 0 1 0 8 1a7 7 0 0 0 0 14Zm1-9.5a1 1 0 1 1-2 0 1 1 0 0 1 2 0Zm-.25 3a.75.75 0 0 0-1.5 0V11a.75.75 0 0 0 1.5 0V8.5Z"),c(e,"clip-rule","evenodd")},m(r,t){Z(r,e,t)},p:q,d(r){r&&$(e)}}}function Ne(n){let e,r;return e=new J({props:{height:"h-5",$$slots:{default:[ze]},$$scope:{ctx:n}}}),{c(){b(e.$$.fragment)},l(t){x(e.$$.fragment,t)},m(t,l){E(e,t,l),r=!0},p(t,[l]){const a={};l&1&&(a.$$scope={dirty:l,ctx:t}),e.$set(a)},i(t){r||(_(e.$$.fragment,t),r=!0)},o(t){p(e.$$.fragment,t),r=!1},d(t){M(e,t)}}}class Be extends T{constructor(e){super(),z(this,e,null,Ne,O,{})}}const re=de(Ze,n=>{const e=n.url.pathname,r=e.lastIndexOf("/");return e[r+1].toUpperCase()+e.substring(r+2)});function je(n){let e,r,t,l,a,s,u,f,o,h="Info alert! Change a few things up and try submitting again.",d;return u=new Be({}),{c(){e=L("header"),r=L("section"),t=L("h1"),l=fe(n[0]),a=C(),s=L("div"),b(u.$$.fragment),f=C(),o=L("span"),o.textContent=h,this.h()},l(i){e=V(i,"HEADER",{class:!0});var m=v(e);r=V(m,"SECTION",{class:!0});var A=v(r);t=V(A,"H1",{class:!0});var H=v(t);l=ie(H,n[0]),H.forEach($),a=k(A),s=V(A,"DIV",{class:!0,role:!0});var y=v(s);x(u.$$.fragment,y),f=k(y),o=V(y,"SPAN",{class:!0,"data-svelte-h":!0}),ue(o)!=="svelte-zqlozd"&&(o.textContent=h),y.forEach($),A.forEach($),m.forEach($),this.h()},h(){c(t,"class","text-xl font-semibold"),c(o,"class","text-sm"),c(s,"class","flex items-center gap-1 rounded-lg border border-text-info p-2 text-text-info"),c(s,"role","alert"),c(r,"class","flex h-full items-center justify-between gap-4"),c(e,"class","min-w-max overflow-auto border-b border-bg-accent px-4 py-2")},m(i,m){Z(i,e,m),I(e,r),I(r,t),I(t,l),I(r,a),I(r,s),E(u,s,null),I(s,f),I(s,o),d=!0},p(i,[m]){(!d||m&1)&&$e(l,i[0])},i(i){d||(_(u.$$.fragment,i),d=!0)},o(i){p(u.$$.fragment,i),d=!1},d(i){i&&$(e),M(u)}}}function ye(n,e,r){let t;return W(n,re,l=>r(0,t=l)),[t]}class Pe extends T{constructor(e){super(),z(this,e,ye,je,O,{})}}function De(n){let e;return{c(){e=B("path"),this.h()},l(r){e=j(r,"path",{"fill-rule":!0,d:!0,"clip-rule":!0}),v(e).forEach($),this.h()},h(){c(e,"fill-rule","evenodd"),c(e,"d","M7.199 2H8.8a.2.2 0 0 1 .2.2c0 1.808 1.958 2.939 3.524 2.034a.199.199 0 0 1 .271.073l.802 1.388a.199.199 0 0 1-.073.272c-1.566.904-1.566 3.164 0 4.069a.199.199 0 0 1 .073.271l-.802 1.388a.199.199 0 0 1-.271.073C10.958 10.863 9 11.993 9 13.8a.2.2 0 0 1-.199.2H7.2a.199.199 0 0 1-.2-.2c0-1.808-1.958-2.938-3.524-2.034a.199.199 0 0 1-.272-.073l-.8-1.388a.199.199 0 0 1 .072-.271c1.566-.905 1.566-3.165 0-4.07a.199.199 0 0 1-.073-.271l.801-1.388a.199.199 0 0 1 .272-.073C5.042 5.138 7 4.007 7 2.2c0-.11.089-.199.199-.199ZM5.5 2.2c0-.94.76-1.7 1.699-1.7H8.8c.94 0 1.7.76 1.7 1.7a.85.85 0 0 0 1.274.735 1.699 1.699 0 0 1 2.32.622l.802 1.388c.469.813.19 1.851-.622 2.32a.85.85 0 0 0 0 1.472 1.7 1.7 0 0 1 .622 2.32l-.802 1.388a1.699 1.699 0 0 1-2.32.622.85.85 0 0 0-1.274.735c0 .939-.76 1.7-1.699 1.7H7.2a1.7 1.7 0 0 1-1.699-1.7.85.85 0 0 0-1.274-.735 1.698 1.698 0 0 1-2.32-.622l-.802-1.388a1.699 1.699 0 0 1 .622-2.32.85.85 0 0 0 0-1.471 1.699 1.699 0 0 1-.622-2.321l.801-1.388a1.699 1.699 0 0 1 2.32-.622A.85.85 0 0 0 5.5 2.2Zm4 5.8a1.5 1.5 0 1 1-3 0 1.5 1.5 0 0 1 3 0ZM11 8a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z"),c(e,"clip-rule","evenodd")},m(r,t){Z(r,e,t)},p:q,d(r){r&&$(e)}}}function qe(n){let e,r;return e=new J({props:{$$slots:{default:[De]},$$scope:{ctx:n}}}),{c(){b(e.$$.fragment)},l(t){x(e.$$.fragment,t)},m(t,l){E(e,t,l),r=!0},p(t,[l]){const a={};l&1&&(a.$$scope={dirty:l,ctx:t}),e.$set(a)},i(t){r||(_(e.$$.fragment,t),r=!0)},o(t){p(e.$$.fragment,t),r=!1},d(t){M(e,t)}}}class Je extends T{constructor(e){super(),z(this,e,null,qe,O,{})}}function Ue(n){let e;return{c(){e=B("path"),this.h()},l(r){e=j(r,"path",{"fill-rule":!0,d:!0,"clip-rule":!0}),v(e).forEach($),this.h()},h(){c(e,"fill-rule","evenodd"),c(e,"d","M10 .333A9.911 9.911 0 0 0 6.866 19.65c.5.092.678-.215.678-.477 0-.237-.01-1.017-.014-1.845-2.757.6-3.338-1.169-3.338-1.169a2.627 2.627 0 0 0-1.1-1.451c-.9-.615.07-.6.07-.6a2.084 2.084 0 0 1 1.518 1.021 2.11 2.11 0 0 0 2.884.823c.044-.503.268-.973.63-1.325-2.2-.25-4.516-1.1-4.516-4.9A3.832 3.832 0 0 1 4.7 7.068a3.56 3.56 0 0 1 .095-2.623s.832-.266 2.726 1.016a9.409 9.409 0 0 1 4.962 0c1.89-1.282 2.717-1.016 2.717-1.016.366.83.402 1.768.1 2.623a3.827 3.827 0 0 1 1.02 2.659c0 3.807-2.319 4.644-4.525 4.889a2.366 2.366 0 0 1 .673 1.834c0 1.326-.012 2.394-.012 2.72 0 .263.18.572.681.475A9.911 9.911 0 0 0 10 .333Z"),c(e,"clip-rule","evenodd")},m(r,t){Z(r,e,t)},p:q,d(r){r&&$(e)}}}function Ge(n){let e,r;return e=new J({props:{viewBox:"0 0 20 20",$$slots:{default:[Ue]},$$scope:{ctx:n}}}),{c(){b(e.$$.fragment)},l(t){x(e.$$.fragment,t)},m(t,l){E(e,t,l),r=!0},p(t,[l]){const a={};l&1&&(a.$$scope={dirty:l,ctx:t}),e.$set(a)},i(t){r||(_(e.$$.fragment,t),r=!0)},o(t){p(e.$$.fragment,t),r=!1},d(t){M(e,t)}}}class Fe extends T{constructor(e){super(),z(this,e,null,Ge,O,{})}}const pe=(n,e)=>{const r=localStorage[n];r||(localStorage[n]=JSON.stringify(e));const{subscribe:t,set:l,update:a}=ge(r?JSON.parse(r):e);return{subscribe:t,set:s=>{localStorage[n]=JSON.stringify(s),l(s)},update:a}};function Re(n){let e;return{c(){e=B("path"),this.h()},l(r){e=j(r,"path",{"fill-rule":!0,d:!0,"clip-rule":!0}),v(e).forEach($),this.h()},h(){c(e,"fill-rule","evenodd"),c(e,"d","M8 3a.75.75 0 0 1-.75-.75V.75a.75.75 0 1 1 1.5 0v1.5A.75.75 0 0 1 8 3Zm0 7.5a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5ZM8 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm-.75 3.25a.75.75 0 0 0 1.5 0v-1.5a.75.75 0 0 0-1.5 0v1.5ZM13 8a.75.75 0 0 1 .75-.75h1.5a.75.75 0 0 1 0 1.5h-1.5A.75.75 0 0 1 13 8ZM.75 7.25a.75.75 0 1 0 0 1.5h1.5a.75.75 0 0 0 0-1.5H.75Zm10.786-2.786a.75.75 0 0 1 0-1.06l1.06-1.06a.75.75 0 0 1 1.06 1.06l-1.06 1.06a.75.75 0 0 1-1.06 0Zm-9.193 8.132a.75.75 0 0 0 1.06 1.06l1.062-1.06a.75.75 0 0 0-1.061-1.06l-1.06 1.06Zm9.193-1.06a.75.75 0 0 1 1.06 0l1.06 1.06a.75.75 0 0 1-1.06 1.06l-1.06-1.06a.75.75 0 0 1 0-1.06ZM3.404 2.343a.75.75 0 0 0-1.06 1.06l1.06 1.061a.75.75 0 1 0 1.06-1.06l-1.06-1.06Z"),c(e,"clip-rule","evenodd")},m(r,t){Z(r,e,t)},p:q,d(r){r&&$(e)}}}function We(n){let e,r;return e=new J({props:{$$slots:{default:[Re]},$$scope:{ctx:n}}}),{c(){b(e.$$.fragment)},l(t){x(e.$$.fragment,t)},m(t,l){E(e,t,l),r=!0},p(t,[l]){const a={};l&1&&(a.$$scope={dirty:l,ctx:t}),e.$set(a)},i(t){r||(_(e.$$.fragment,t),r=!0)},o(t){p(e.$$.fragment,t),r=!1},d(t){M(e,t)}}}class Ke extends T{constructor(e){super(),z(this,e,null,We,O,{})}}function Qe(n){let e;return{c(){e=B("path"),this.h()},l(r){e=j(r,"path",{"fill-rule":!0,d:!0,"clip-rule":!0}),v(e).forEach($),this.h()},h(){c(e,"fill-rule","evenodd"),c(e,"d","M8 13.5a5.5 5.5 0 0 0 2.263-10.514 5.5 5.5 0 0 1-7.278 7.278A5.501 5.501 0 0 0 8 13.5ZM1.045 8.795a7.001 7.001 0 1 0 7.75-7.75l-.028-.003A7.078 7.078 0 0 0 8 1c-.527 0-.59.842-.185 1.18a4.02 4.02 0 0 1 .342.322A4 4 0 1 1 2.18 7.814C1.842 7.41 1 7.474 1 8a7.078 7.078 0 0 0 .045.794Z"),c(e,"clip-rule","evenodd")},m(r,t){Z(r,e,t)},p:q,d(r){r&&$(e)}}}function Xe(n){let e,r;return e=new J({props:{$$slots:{default:[Qe]},$$scope:{ctx:n}}}),{c(){b(e.$$.fragment)},l(t){x(e.$$.fragment,t)},m(t,l){E(e,t,l),r=!0},p(t,[l]){const a={};l&1&&(a.$$scope={dirty:l,ctx:t}),e.$set(a)},i(t){r||(_(e.$$.fragment,t),r=!0)},o(t){p(e.$$.fragment,t),r=!1},d(t){M(e,t)}}}class Ye extends T{constructor(e){super(),z(this,e,null,Xe,O,{})}}function et(n){let e;return{c(){e=B("path"),this.h()},l(r){e=j(r,"path",{"fill-rule":!0,d:!0,"clip-rule":!0}),v(e).forEach($),this.h()},h(){c(e,"fill-rule","evenodd"),c(e,"d","M12 3H4a1.5 1.5 0 0 0-1.5 1.5v4A1.5 1.5 0 0 0 4 10h8a1.5 1.5 0 0 0 1.5-1.5v-4A1.5 1.5 0 0 0 12 3ZM4 1.5a3 3 0 0 0-3 3v4a3 3 0 0 0 3 3h3.25V13h-2.5a.75.75 0 0 0 0 1.5h6.5a.75.75 0 0 0 0-1.5h-2.5v-1.5H12a3 3 0 0 0 3-3v-4a3 3 0 0 0-3-3H4Z"),c(e,"clip-rule","evenodd")},m(r,t){Z(r,e,t)},p:q,d(r){r&&$(e)}}}function tt(n){let e,r;return e=new J({props:{$$slots:{default:[et]},$$scope:{ctx:n}}}),{c(){b(e.$$.fragment)},l(t){x(e.$$.fragment,t)},m(t,l){E(e,t,l),r=!0},p(t,[l]){const a={};l&1&&(a.$$scope={dirty:l,ctx:t}),e.$set(a)},i(t){r||(_(e.$$.fragment,t),r=!0)},o(t){p(e.$$.fragment,t),r=!1},d(t){M(e,t)}}}class rt extends T{constructor(e){super(),z(this,e,null,tt,O,{})}}function nt(n){let e,r,t,l,a,s;var u=n[1][n[0]];function f(o,h){return{}}return u&&(r=ne(u,f())),{c(){e=L("button"),r&&b(r.$$.fragment),this.h()},l(o){e=V(o,"BUTTON",{class:!0,title:!0});var h=v(e);r&&x(r.$$.fragment,h),h.forEach($),this.h()},h(){c(e,"class","rounded-lg p-2 hover:bg-bg-medium"),c(e,"title",t=`Color theme: ${n[0]}`)},m(o,h){Z(o,e,h),r&&E(r,e,null),l=!0,a||(s=Ee(e,"click",n[2]),a=!0)},p(o,[h]){if(h&1&&u!==(u=o[1][o[0]])){if(r){he();const d=r;p(d.$$.fragment,1,0,()=>{M(d,1)}),me()}u?(r=ne(u,f()),b(r.$$.fragment),_(r.$$.fragment,1),E(r,e,null)):r=null}(!l||h&1&&t!==(t=`Color theme: ${o[0]}`))&&c(e,"title",t)},i(o){l||(r&&_(r.$$.fragment,o),l=!0)},o(o){r&&p(r.$$.fragment,o),l=!1},d(o){o&&$(e),r&&M(r),a=!1,s()}}}const se=pe("theme","system");function lt(n,e,r){let t;return W(n,se,s=>r(0,t=s)),document.querySelector("body")?.setAttribute("data-theme",t),[t,{light:Ke,dark:Ye,system:rt},()=>{we(se,t=t==="system"?"light":t==="light"?"dark":"system",t),document.querySelector("body")?.setAttribute("data-theme",t)}]}class at extends T{constructor(e){super(),z(this,e,lt,nt,O,{})}}function st(n){let e,r,t,l,a,s,u,f,o;return t=new Je({}),a=new at({}),f=new Fe({}),{c(){e=L("nav"),r=L("a"),b(t.$$.fragment),l=C(),b(a.$$.fragment),s=C(),u=L("a"),b(f.$$.fragment),this.h()},l(h){e=V(h,"NAV",{class:!0});var d=v(e);r=V(d,"A",{href:!0,class:!0,title:!0});var i=v(r);x(t.$$.fragment,i),i.forEach($),l=k(d),x(a.$$.fragment,d),s=k(d),u=V(d,"A",{href:!0,class:!0,title:!0,target:!0,rel:!0});var m=v(u);x(f.$$.fragment,m),m.forEach($),d.forEach($),this.h()},h(){c(r,"href","/settings"),c(r,"class","rounded-lg p-2 hover:bg-bg-medium"),c(r,"title","Settings"),c(u,"href","https://github.com/WLM1ke/poptimizer"),c(u,"class","rounded-lg p-2 hover:bg-bg-medium"),c(u,"title","Go to GitHub"),c(u,"target","_blank"),c(u,"rel","noopener"),c(e,"class","flex w-full items-center justify-around border-t border-bg-medium pt-2")},m(h,d){Z(h,e,d),I(e,r),E(t,r,null),I(e,l),E(a,e,null),I(e,s),I(e,u),E(f,u,null),o=!0},p:q,i(h){o||(_(t.$$.fragment,h),_(a.$$.fragment,h),_(f.$$.fragment,h),o=!0)},o(h){p(t.$$.fragment,h),p(a.$$.fragment,h),p(f.$$.fragment,h),o=!1},d(h){h&&$(e),M(t),M(a),M(f)}}}class ot extends T{constructor(e){super(),z(this,e,null,st,O,{})}}function ct(n){let e,r,t,l,a,s;const u=n[5].default,f=X(u,n,n[4],null);return{c(){e=L("li"),r=L("a"),f&&f.c(),t=C(),l=L("span"),a=fe(n[0]),this.h()},l(o){e=V(o,"LI",{});var h=v(e);r=V(h,"A",{href:!0,class:!0});var d=v(r);f&&f.l(d),t=k(d),l=V(d,"SPAN",{class:!0});var i=v(l);a=ie(i,n[0]),i.forEach($),d.forEach($),h.forEach($),this.h()},h(){c(l,"class","text-text-main"),c(r,"href",n[1]),c(r,"class","flex items-center gap-2 rounded-lg p-2 font-medium text-text-muted hover:bg-bg-medium"),Q(r,"px-4",n[2]),Q(r,"bg-bg-medium",n[3]===n[0])},m(o,h){Z(o,e,h),I(e,r),f&&f.m(r,null),I(r,t),I(r,l),I(l,a),s=!0},p(o,[h]){f&&f.p&&(!s||h&16)&&Y(f,u,o,o[4],s?te(u,o[4],h,null):ee(o[4]),null),(!s||h&1)&&$e(a,o[0]),(!s||h&2)&&c(r,"href",o[1]),(!s||h&4)&&Q(r,"px-4",o[2]),(!s||h&9)&&Q(r,"bg-bg-medium",o[3]===o[0])},i(o){s||(_(f,o),s=!0)},o(o){p(f,o),s=!1},d(o){o&&$(e),f&&f.d(o)}}}function ut(n,e,r){let t;W(n,re,o=>r(3,t=o));let{$$slots:l={},$$scope:a}=e,{title:s}=e,{href:u}=e,{subItem:f=!1}=e;return n.$$set=o=>{"title"in o&&r(0,s=o.title),"href"in o&&r(1,u=o.href),"subItem"in o&&r(2,f=o.subItem),"$$scope"in o&&r(4,a=o.$$scope)},[s,u,f,t,a,l]}class R extends T{constructor(e){super(),z(this,e,ut,ct,O,{title:0,href:1,subItem:2})}}function ft(n){let e;return{c(){e=B("path"),this.h()},l(r){e=j(r,"path",{"fill-rule":!0,d:!0,"clip-rule":!0}),v(e).forEach($),this.h()},h(){c(e,"fill-rule","evenodd"),c(e,"d","M13.45 8.75a5.501 5.501 0 1 1-6.2-6.2V8c0 .414.336.75.75.75h5.45Zm0-1.5h-4.7v-4.7a5.503 5.503 0 0 1 4.7 4.7ZM15 8A7 7 0 1 1 1 8a7 7 0 0 1 14 0Z"),c(e,"clip-rule","evenodd")},m(r,t){Z(r,e,t)},p:q,d(r){r&&$(e)}}}function it(n){let e,r;return e=new J({props:{$$slots:{default:[ft]},$$scope:{ctx:n}}}),{c(){b(e.$$.fragment)},l(t){x(e.$$.fragment,t)},m(t,l){E(e,t,l),r=!0},p(t,[l]){const a={};l&1&&(a.$$scope={dirty:l,ctx:t}),e.$set(a)},i(t){r||(_(e.$$.fragment,t),r=!0)},o(t){p(e.$$.fragment,t),r=!1},d(t){M(e,t)}}}class $t extends T{constructor(e){super(),z(this,e,null,it,O,{})}}function ht(n){let e;return{c(){e=B("path"),this.h()},l(r){e=j(r,"path",{"fill-rule":!0,d:!0,"clip-rule":!0}),v(e).forEach($),this.h()},h(){c(e,"fill-rule","evenodd"),c(e,"d","M5.515 3.5h.621l.44-.44 1.07-1.07a.5.5 0 0 1 .708 0l1.07 1.07.44.44H12a.5.5 0 0 1 .5.5v2.136l.44.44 1.07 1.07a.5.5 0 0 1 0 .708l-1.07 1.07-.44.44V12a.5.5 0 0 1-.5.5H9.864l-.44.44-1.07 1.07a.5.5 0 0 1-.708 0l-1.07-1.07-.44-.44H4a.5.5 0 0 1-.5-.5V9.864l-.44-.44-1.07-1.07a.5.5 0 0 1 0-.708l1.07-1.07.44-.44V4a.5.5 0 0 1 .5-.5h1.515Zm3.9-2.571a2 2 0 0 0-2.83 0L5.516 2H4a2 2 0 0 0-2 2v1.515L.929 6.585a2 2 0 0 0 0 2.83L2 10.484V12a2 2 0 0 0 2 2h1.515l1.07 1.071a2 2 0 0 0 2.83 0L10.484 14H12a2 2 0 0 0 2-2v-1.515l1.071-1.07a2 2 0 0 0 0-2.83L14 5.516V4a2 2 0 0 0-2-2h-1.515L9.415.929ZM6.53 10.53l4-4a.75.75 0 1 0-1.06-1.06l-4 4a.75.75 0 1 0 1.06 1.06ZM11 10a1 1 0 1 1-2 0 1 1 0 0 1 2 0ZM6 7a1 1 0 1 0 0-2 1 1 0 0 0 0 2Z"),c(e,"clip-rule","evenodd")},m(r,t){Z(r,e,t)},p:q,d(r){r&&$(e)}}}function mt(n){let e,r;return e=new J({props:{$$slots:{default:[ht]},$$scope:{ctx:n}}}),{c(){b(e.$$.fragment)},l(t){x(e.$$.fragment,t)},m(t,l){E(e,t,l),r=!0},p(t,[l]){const a={};l&1&&(a.$$scope={dirty:l,ctx:t}),e.$set(a)},i(t){r||(_(e.$$.fragment,t),r=!0)},o(t){p(e.$$.fragment,t),r=!1},d(t){M(e,t)}}}class dt extends T{constructor(e){super(),z(this,e,null,mt,O,{})}}function gt(n){let e;return{c(){e=B("path"),this.h()},l(r){e=j(r,"path",{"fill-rule":!0,d:!0,"clip-rule":!0}),v(e).forEach($),this.h()},h(){c(e,"fill-rule","evenodd"),c(e,"d","M4.61 2.503a6.473 6.473 0 0 1 3.383-.984 6.48 6.48 0 0 1 4.515 1.77l-.004-.559a.75.75 0 1 1 1.5-.013l.021 2.5a.75.75 0 0 1-.743.756l-2.497.022a.75.75 0 1 1-.013-1.5l.817-.007a4.983 4.983 0 0 0-3.583-1.469 4.973 4.973 0 0 0-2.602.756.75.75 0 0 1-.795-1.272Zm9.097 8.716a6.48 6.48 0 0 0 .84-3.422.75.75 0 1 0-1.5.053 4.973 4.973 0 0 1-.646 2.63 4.983 4.983 0 0 1-3.064 2.37l.403-.712a.75.75 0 0 0-1.306-.738l-1.229 2.173a.75.75 0 0 0 .283 1.022l2.176 1.23a.75.75 0 1 0 .739-1.305l-.487-.275a6.48 6.48 0 0 0 3.79-3.026Zm-11.258.099a6.473 6.473 0 0 0 2.544 2.438.75.75 0 0 0 .704-1.325 4.973 4.973 0 0 1-1.955-1.875 4.983 4.983 0 0 1-.52-3.838l.415.705a.75.75 0 1 0 1.292-.762l-1.267-2.15a.75.75 0 0 0-1.027-.266L.481 5.513a.75.75 0 1 0 .761 1.293l.483-.284a6.48 6.48 0 0 0 .724 4.796Z"),c(e,"clip-rule","evenodd")},m(r,t){Z(r,e,t)},p:q,d(r){r&&$(e)}}}function pt(n){let e,r;return e=new J({props:{$$slots:{default:[gt]},$$scope:{ctx:n}}}),{c(){b(e.$$.fragment)},l(t){x(e.$$.fragment,t)},m(t,l){E(e,t,l),r=!0},p(t,[l]){const a={};l&1&&(a.$$scope={dirty:l,ctx:t}),e.$set(a)},i(t){r||(_(e.$$.fragment,t),r=!0)},o(t){p(e.$$.fragment,t),r=!1},d(t){M(e,t)}}}class _t extends T{constructor(e){super(),z(this,e,null,pt,O,{})}}function vt(n){let e;return{c(){e=B("path"),this.h()},l(r){e=j(r,"path",{"fill-rule":!0,d:!0,"clip-rule":!0}),v(e).forEach($),this.h()},h(){c(e,"fill-rule","evenodd"),c(e,"d","M13.5 8a5.5 5.5 0 1 1-11 0 5.5 5.5 0 0 1 11 0ZM15 8A7 7 0 1 1 1 8a7 7 0 0 1 14 0ZM6.75 4a.75.75 0 0 0-.75.75v2.5h-.125a.75.75 0 0 0 0 1.5H6v.5h-.125a.75.75 0 0 0 0 1.5H6v.5a.75.75 0 0 0 1.5 0v-.5H9a.75.75 0 0 0 0-1.5H7.5v-.5h1.125a2.375 2.375 0 1 0 0-4.75H6.75Zm1.875 3.25H7.5V5.5h1.125a.875.875 0 1 1 0 1.75Z"),c(e,"clip-rule","evenodd")},m(r,t){Z(r,e,t)},p:q,d(r){r&&$(e)}}}function wt(n){let e,r;return e=new J({props:{$$slots:{default:[vt]},$$scope:{ctx:n}}}),{c(){b(e.$$.fragment)},l(t){x(e.$$.fragment,t)},m(t,l){E(e,t,l),r=!0},p(t,[l]){const a={};l&1&&(a.$$scope={dirty:l,ctx:t}),e.$set(a)},i(t){r||(_(e.$$.fragment,t),r=!0)},o(t){p(e.$$.fragment,t),r=!1},d(t){M(e,t)}}}class bt extends T{constructor(e){super(),z(this,e,null,wt,O,{})}}function Et(n){let e;return{c(){e=B("path"),this.h()},l(r){e=j(r,"path",{"fill-rule":!0,d:!0,"clip-rule":!0}),v(e).forEach($),this.h()},h(){c(e,"fill-rule","evenodd"),c(e,"d","m2.789 5.283 4.037-2.02A2.5 2.5 0 0 1 7.944 3h.112c.388 0 .77.09 1.118.264l4.037 2.019a.522.522 0 0 1 0 .934l-4.037 2.02a2.5 2.5 0 0 1-1.118.263h-.112a2.5 2.5 0 0 1-1.118-.264L2.79 6.217a.523.523 0 0 1 0-.934ZM1 5.75c0-.766.433-1.466 1.118-1.809l4.037-2.019a4 4 0 0 1 1.79-.422h.11a4 4 0 0 1 1.79.422l4.037 2.019a2.023 2.023 0 0 1 0 3.618l-.882.44.882.442a2.023 2.023 0 0 1 0 3.618l-4.037 2.019a4 4 0 0 1-1.79.422h-.11a4 4 0 0 1-1.79-.422l-4.037-2.02a2.023 2.023 0 0 1 0-3.617L3 8l-.882-.441A2.023 2.023 0 0 1 1 5.75Zm3.677 3.088-1.888.945a.523.523 0 0 0 0 .934l4.037 2.019A2.5 2.5 0 0 0 7.944 13h.112a2.5 2.5 0 0 0 1.118-.264l4.037-2.019a.523.523 0 0 0 0-.934l-1.888-.945-1.478.74a4 4 0 0 1-1.79.422h-.11a4 4 0 0 1-1.79-.422l-1.478-.74Z"),c(e,"clip-rule","evenodd")},m(r,t){Z(r,e,t)},p:q,d(r){r&&$(e)}}}function Mt(n){let e,r;return e=new J({props:{$$slots:{default:[Et]},$$scope:{ctx:n}}}),{c(){b(e.$$.fragment)},l(t){x(e.$$.fragment,t)},m(t,l){E(e,t,l),r=!0},p(t,[l]){const a={};l&1&&(a.$$scope={dirty:l,ctx:t}),e.$set(a)},i(t){r||(_(e.$$.fragment,t),r=!0)},o(t){p(e.$$.fragment,t),r=!1},d(t){M(e,t)}}}class Zt extends T{constructor(e){super(),z(this,e,null,Mt,O,{})}}function oe(n,e,r){const t=n.slice();return t[1]=e[r],t}function xt(n){let e,r;return e=new $t({}),{c(){b(e.$$.fragment)},l(t){x(e.$$.fragment,t)},m(t,l){E(e,t,l),r=!0},i(t){r||(_(e.$$.fragment,t),r=!0)},o(t){p(e.$$.fragment,t),r=!1},d(t){M(e,t)}}}function At(n){let e,r;return e=new Zt({}),{c(){b(e.$$.fragment)},l(t){x(e.$$.fragment,t)},m(t,l){E(e,t,l),r=!0},i(t){r||(_(e.$$.fragment,t),r=!0)},o(t){p(e.$$.fragment,t),r=!1},d(t){M(e,t)}}}function ce(n,e){let r,t,l;return t=new R({props:{title:e[1],href:"/portfolio/"+e[1].toLowerCase(),subItem:!0,$$slots:{default:[At]},$$scope:{ctx:e}}}),{key:n,first:null,c(){r=le(),b(t.$$.fragment),this.h()},l(a){r=le(),x(t.$$.fragment,a),this.h()},h(){this.first=r},m(a,s){Z(a,r,s),E(t,a,s),l=!0},p(a,s){e=a;const u={};s&1&&(u.title=e[1]),s&1&&(u.href="/portfolio/"+e[1].toLowerCase()),s&16&&(u.$$scope={dirty:s,ctx:e}),t.$set(u)},i(a){l||(_(t.$$.fragment,a),l=!0)},o(a){p(t.$$.fragment,a),l=!1},d(a){a&&$(r),M(t,a)}}}function St(n){let e,r;return e=new dt({}),{c(){b(e.$$.fragment)},l(t){x(e.$$.fragment,t)},m(t,l){E(e,t,l),r=!0},i(t){r||(_(e.$$.fragment,t),r=!0)},o(t){p(e.$$.fragment,t),r=!1},d(t){M(e,t)}}}function It(n){let e,r;return e=new _t({}),{c(){b(e.$$.fragment)},l(t){x(e.$$.fragment,t)},m(t,l){E(e,t,l),r=!0},i(t){r||(_(e.$$.fragment,t),r=!0)},o(t){p(e.$$.fragment,t),r=!1},d(t){M(e,t)}}}function Ht(n){let e,r;return e=new bt({}),{c(){b(e.$$.fragment)},l(t){x(e.$$.fragment,t)},m(t,l){E(e,t,l),r=!0},i(t){r||(_(e.$$.fragment,t),r=!0)},o(t){p(e.$$.fragment,t),r=!1},d(t){M(e,t)}}}function Ct(n){let e,r,t,l,a,s=[],u=new Map,f,o,h,d,i,m,A,H,y,G;l=new R({props:{title:"Portfolio",href:"/portfolio",$$slots:{default:[xt]},$$scope:{ctx:n}}});let U=ae(n[0]);const F=g=>g[1];for(let g=0;g<U.length;g+=1){let w=oe(n,U,g),N=F(w);u.set(N,s[g]=ce(N,w))}return o=new R({props:{title:"Forecast",href:"/forecast",$$slots:{default:[St]},$$scope:{ctx:n}}}),d=new R({props:{title:"Optimization",href:"/optimization",$$slots:{default:[It]},$$scope:{ctx:n}}}),A=new R({props:{title:"Dividends",href:"/dividends",$$slots:{default:[Ht]},$$scope:{ctx:n}}}),y=new ot({}),{c(){e=L("aside"),r=L("nav"),t=L("ul"),b(l.$$.fragment),a=C();for(let g=0;g<s.length;g+=1)s[g].c();f=C(),b(o.$$.fragment),h=C(),b(d.$$.fragment),i=C(),m=L("ul"),b(A.$$.fragment),H=C(),b(y.$$.fragment),this.h()},l(g){e=V(g,"ASIDE",{class:!0});var w=v(e);r=V(w,"NAV",{class:!0});var N=v(r);t=V(N,"UL",{class:!0});var S=v(t);x(l.$$.fragment,S),a=k(S);for(let P=0;P<s.length;P+=1)s[P].l(S);f=k(S),x(o.$$.fragment,S),h=k(S),x(d.$$.fragment,S),S.forEach($),i=k(N),m=V(N,"UL",{class:!0});var D=v(m);x(A.$$.fragment,D),D.forEach($),N.forEach($),H=k(w),x(y.$$.fragment,w),w.forEach($),this.h()},h(){c(t,"class","flex flex-col gap-1"),c(m,"class","border-t border-bg-medium pt-2"),c(r,"class","flex flex-col gap-2"),c(e,"class","flex flex-col justify-between border-r border-bg-accent bg-bg-sidebar p-2")},m(g,w){Z(g,e,w),I(e,r),I(r,t),E(l,t,null),I(t,a);for(let N=0;N<s.length;N+=1)s[N]&&s[N].m(t,null);I(t,f),E(o,t,null),I(t,h),E(d,t,null),I(r,i),I(r,m),E(A,m,null),I(e,H),E(y,e,null),G=!0},p(g,[w]){const N={};w&16&&(N.$$scope={dirty:w,ctx:g}),l.$set(N),w&1&&(U=ae(g[0]),he(),s=Ae(s,w,F,1,g,U,u,t,xe,ce,f,oe),me());const S={};w&16&&(S.$$scope={dirty:w,ctx:g}),o.$set(S);const D={};w&16&&(D.$$scope={dirty:w,ctx:g}),d.$set(D);const P={};w&16&&(P.$$scope={dirty:w,ctx:g}),A.$set(P)},i(g){if(!G){_(l.$$.fragment,g);for(let w=0;w<U.length;w+=1)_(s[w]);_(o.$$.fragment,g),_(d.$$.fragment,g),_(A.$$.fragment,g),_(y.$$.fragment,g),G=!0}},o(g){p(l.$$.fragment,g);for(let w=0;w<s.length;w+=1)p(s[w]);p(o.$$.fragment,g),p(d.$$.fragment,g),p(A.$$.fragment,g),p(y.$$.fragment,g),G=!1},d(g){g&&$(e),M(l);for(let w=0;w<s.length;w+=1)s[w].d();M(o),M(d),M(A),M(y)}}}function kt(n,e,r){let{accounts:t}=e;return n.$$set=l=>{"accounts"in l&&r(0,t=l.accounts)},[t]}class Lt extends T{constructor(e){super(),z(this,e,kt,Ct,O,{accounts:0})}}const Vt=ge([]),Ot=n=>Vt.update(e=>[...e,n]),_e=pe("portfolio",{securities:{},accounts:{}}),Tt=async()=>{try{const n=await fetch("/api/portfolio");if(!n.ok)throw new Error(await n.text());_e.set(await n.json())}catch(n){let e;n instanceof Error?e=n.message:e=JSON.stringify(n),Ot(e)}},zt=de(_e,n=>Object.keys(n.accounts).toSorted());function Nt(n){let e,r,t,l,a,s,u,f,o,h;document.title=e="POptimizer - "+n[0],l=new Te({}),s=new Pe({}),f=new Lt({props:{accounts:n[1]}});const d=n[3].default,i=X(d,n,n[2],null);return{c(){r=C(),t=L("section"),b(l.$$.fragment),a=C(),b(s.$$.fragment),u=C(),b(f.$$.fragment),o=C(),i&&i.c(),this.h()},l(m){Me("svelte-1kjrvgf",document.head).forEach($),r=k(m),t=V(m,"SECTION",{class:!0});var H=v(t);x(l.$$.fragment,H),a=k(H),x(s.$$.fragment,H),u=k(H),x(f.$$.fragment,H),o=k(H),i&&i.l(H),H.forEach($),this.h()},h(){c(t,"class","grid h-screen w-screen grid-cols-layout grid-rows-layout")},m(m,A){Z(m,r,A),Z(m,t,A),E(l,t,null),I(t,a),E(s,t,null),I(t,u),E(f,t,null),I(t,o),i&&i.m(t,null),h=!0},p(m,[A]){(!h||A&1)&&e!==(e="POptimizer - "+m[0])&&(document.title=e);const H={};A&2&&(H.accounts=m[1]),f.$set(H),i&&i.p&&(!h||A&4)&&Y(i,d,m,m[2],h?te(d,m[2],A,null):ee(m[2]),null)},i(m){h||(_(l.$$.fragment,m),_(s.$$.fragment,m),_(f.$$.fragment,m),_(i,m),h=!0)},o(m){p(l.$$.fragment,m),p(s.$$.fragment,m),p(f.$$.fragment,m),p(i,m),h=!1},d(m){m&&($(r),$(t)),M(l),M(s),M(f),i&&i.d(m)}}}function Bt(n,e,r){let t,l;W(n,re,u=>r(0,t=u)),W(n,zt,u=>r(1,l=u));let{$$slots:a={},$$scope:s}=e;return be(()=>{Tt()}),n.$$set=u=>{"$$scope"in u&&r(2,s=u.$$scope)},[t,l,s,a]}class Jt extends T{constructor(e){super(),z(this,e,Bt,Nt,O,{})}}export{Jt as component,qt as universal};
