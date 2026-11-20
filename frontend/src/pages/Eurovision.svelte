<script>
  // 0.28 : « Good Evening Europe! », l'édition spéciale Eurovision — un numéro par soirée Douze points clôturée.
  // Relecture élément par élément (commune avec la Gazette et La Récidive) à gauche, aperçu des 4 pages à droite.
  // Tout ce qui est calculé (podiums, palmarès, qualifiés…) vient de Douze points : on le valide tel quel. On choisit
  // seulement le N°, les images gardées, la photo de chaque duo et les 2 ou 3 commentaires (tirés au hasard, sans IA).
  // « Approuver » contrôle qu'aucune page ne déborde ; puis la parution est notée dans carnet pour chaque invité lié.
  import { onMount, setContext } from 'svelte'
  import ArrowLeft from '@lucide/svelte/icons/arrow-left'
  import Download from '@lucide/svelte/icons/download'
  import Shuffle from '@lucide/svelte/icons/shuffle'
  import { api } from '$lib/api.js'
  import { Button } from '$lib/components/ui/button/index.js'
  import Etat from '$lib/Etat.svelte'
  import Element from '$lib/Element.svelte'
  import Relecture from '$lib/Relecture.svelte'
  import { dateLongue } from '$lib/format.js'

  let { id, onchange, ondeconnecte } = $props()
  let d = $state(null)
  let numero = $state('')
  let images = $state({})
  let duos = $state([])
  let commentaires = $state([])
  let modifie = $state(false)
  let message = $state('')
  let attente = $state('')
  let tampon = $state(Date.now())
  let mes = $state(null)
  const trop = $derived(Object.fromEntries((mes ?? []).filter((p) => p.deborde).map((p) => [p.page, p.exces])))
  let valides = $state({})
  let revoir = $state(false)
  const registre = $state({})
  setContext('validation', {
    valides: () => valides, revoir: () => revoir, registre,
    trop: (n) => !!trop[n],
    valider: async (cle, h) => { valides = { ...valides, [cle]: h }; await enregistrer(true) },
  })
  const total = $derived(Object.keys(registre).length)
  const restants = $derived(Object.values(registre).filter((x) => !x).length)
  const fini = $derived(total > 0 && restants === 0)
  let largeur = $state(400)
  const echelle = $derived(Math.min(1, largeur / 600))
  const NOMS = { apero: 'Photo apéro', poster: 'Poster', logo: 'Logo', banniere: 'Bannière' }
  const ROLES = { apero: 'en priorité pour la une', poster: 'en une si pas de photo apéro', logo: 'pastille de la une, fond des duos sans photo', banniere: 'bas de la page 4' }

  async function lire() {
    try {
      d = await api.get(`/api/eurovisions/${id}`)
      numero = d.numero.numero_main || ''
      images = Object.fromEntries(d.vue.images.map((i) => [i.sorte, i.garder]))
      duos = d.vue.duos.map((x) => ({ ...x }))
      commentaires = d.vue.commentaires
      valides = { ...(d.numero.valides ?? {}) }
      modifie = false
      tampon = Date.now()
      mesurer()
    } catch (err) {
      if (err.statut === 401) ondeconnecte?.()
      else message = err.message
    }
  }
  async function mesurer() {
    try { mes = (await api.get(`/api/eurovisions/${id}/mesure`)).pages } catch { mes = null }   // sans Chromium : rien
  }
  function toucher() { modifie = true; message = '' }
  const corps = () => ({ numero_main: numero, images: $state.snapshot(images), valides: $state.snapshot(valides),
                         duos: duos.map((x) => ({ cle: x.cle, photo: x.photo, retiree: x.retiree })) })
  async function enregistrer(silencieux = false) {
    attente = 'enregistrer'
    try { await api.put(`/api/eurovisions/${id}`, corps()); await lire(); if (silencieux !== true) message = 'Enregistré.'; onchange?.() }
    catch (err) { message = err.message }
    attente = ''
  }
  async function approuver() {
    if (modifie) await enregistrer(true)
    attente = 'approuver'
    try {
      const r = await api.post(`/api/eurovisions/${id}/approuver`)
      await lire()
      message = `Numéro approuvé : prêt à imprimer. Carnet : ${r.carnet}.`
      onchange?.()
    } catch (err) { message = err.message }
    attente = ''
  }
  async function tirer(geste = {}) {
    if (modifie) await api.put(`/api/eurovisions/${id}`, corps())
    try { await api.post(`/api/eurovisions/${id}/tirer`, geste); await lire() } catch (err) { message = err.message }
  }
  async function refaire() {
    if (!confirm('Refaire ce numéro avec la nouvelle version du résultat ? Il repasse à relire (le numéro déjà imprimé ne change pas).')) return
    try { await api.post(`/api/eurovisions/${id}/refaire`); await lire(); onchange?.() } catch (err) { message = err.message }
  }
  async function ignorerVersion() {
    await api.post(`/api/eurovisions/${id}/ignorer-version`); await lire(); onchange?.()
  }
  function autrePhoto(x) {
    const i = x.photos.indexOf(x.photo)
    const suivante = x.photos[(i + 1) % x.photos.length]
    if (!suivante || suivante === x.photo) { message = 'Pas d\'autre photo pour ce duo dans Immich.'; return }
    x.photo = suivante; x.retiree = false; toucher()
  }
  const n = $derived(d?.numero)
  const v = $derived(d?.vue)
  const cadre = (p) => (trop[p] ? 'border-destructive ring-2 ring-destructive/50' : '')
  onMount(lire)
</script>

{#snippet alerte(p)}
  {#if trop[p]}
    <p class="mb-3 rounded-lg border border-destructive/60 bg-destructive/10 px-3 py-2 text-sm text-destructive" role="alert">
      Page {p} trop pleine à l'impression (il manque environ {Math.ceil(trop[p] / 3.78)} mm) : retire un commentaire ou une image, puis Enregistrer.</p>
  {/if}
{/snippet}

{#snippet liste(titre, items)}
  {#if items?.length}
    <div class="min-w-0"><span class="text-[0.7rem] font-medium tracking-wide text-muted-foreground uppercase">{titre}</span>
      <ol class="mt-0.5 list-decimal pl-5 text-sm">{#each items as x}<li>{x}</li>{/each}</ol></div>
  {/if}
{/snippet}

{#if d}
  <header class="sticky top-0 z-10 -mx-2 mb-5 flex flex-wrap items-end justify-between gap-3 bg-background/90 px-2 py-2 backdrop-blur">
    <div class="min-w-0">
      <a href="#/a-traiter" class="mb-1 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"><ArrowLeft class="size-4" aria-hidden="true" />À traiter</a>
      <p class="etiquette">{v.titre} · {v.livret === 'qualifies' ? 'livret « qualifiés »' : 'livret « finale »'}</p>
      <h1 class="titre flex flex-wrap items-center gap-3">{v.soiree.nom} <Etat etat={n.etat} /></h1>
      <p class="mt-1 text-sm text-muted-foreground">{v.soiree.date ? dateLongue(v.soiree.date) : ''} · résultat de Douze points, version {n.version}{v.avec_jury ? '' : ' · sans jury (rien sur le jury)'}</p>
    </div>
    <div class="flex flex-wrap gap-2">
      <Button variant="outline" onclick={enregistrer} disabled={!modifie || attente !== ''}>{attente === 'enregistrer' ? 'Enregistrement…' : 'Enregistrer'}</Button>
      <Button onclick={approuver} disabled={attente !== '' || n.etat === 'approuve' && !modifie}>
        {attente === 'approuver' ? 'Contrôle…' : n.etat === 'approuve' && !modifie ? 'Approuvé' : 'Approuver'}</Button>
    </div>
  </header>

  {#if n.essai}
    <p class="mb-4 flex flex-wrap items-center justify-between gap-2 rounded-xl border border-primary/60 px-4 py-2 text-sm" role="status">
      <span>Numéro d'essai (simulation) : il ne compte jamais (ni carnet, ni archives, ni À traiter).</span>
      <button type="button" class="text-xs underline hover:text-destructive" onclick={async () => { await api.del(`/api/essais/eurovision/${id}`); location.hash = '#/reglages' }}>Supprimer l'essai</button>
    </p>
  {/if}
  {#if d.nouvelle_version}
    <p class="mb-4 flex flex-wrap items-center justify-between gap-2 rounded-xl border border-primary/60 px-4 py-2 text-sm" role="status">
      <span>Nouvelle version du résultat dans Douze points (version {n.version_dispo}). Ce numéro a paru avec la version {n.version} : il ne change pas tout seul.</span>
      <span class="flex gap-2"><Button size="sm" onclick={refaire}>Refaire le numéro</Button><Button size="sm" variant="outline" onclick={ignorerVersion}>Garder tel quel</Button></span>
    </p>
  {/if}
  {#if message}<p class="mb-4 rounded-xl border px-4 py-2 text-sm" role="status">{message}</p>{/if}
  {#if n.erreur}<p class="mb-4 rounded-xl border border-destructive/60 px-4 py-2 text-sm text-destructive" role="alert">{n.erreur}</p>{/if}

  <div class="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,26rem)]">
    <div class="grid min-w-0 content-start gap-4">
      <Relecture {restants} {total} bind:revoir {approuver} {attente} etat={n.etat} {modifie} journal="le numéro" />
      <div class="grid min-w-0 content-start gap-4" class:hidden={fini && !revoir}>
        <section class="min-w-0 rounded-2xl border bg-card p-4 {cadre(1)}" aria-label="Une">
          {@render alerte(1)}
          <h2 class="etiquette mb-2">Page 1 · la une</h2>
          <Element cle="une" page={1} titre="N° et invité en une" valeur={{ n: numero, u: v.une?.phrase ?? '' }}>
            <label class="grid gap-1 text-sm"><span class="etiquette">N° (imprimé)</span>
              <input class="min-w-0 rounded-lg border bg-background px-2 py-1" maxlength="60" placeholder={v.numero_defaut} bind:value={numero} oninput={toucher} /></label>
            <p class="text-xs text-muted-foreground">Vide : « {v.numero_defaut} » (année, évènement, type).</p>
            <p class="mt-1 text-sm">{v.livret === 'qualifies' ? 'Le meilleur flair' : 'Le plus proche du vrai'} : {v.une ? v.une.phrase : 'personne (aucun classement complet)'}</p>
          </Element>
          <Element cle="images" page={1} titre="Images de l'évènement" valeur={images}>
            {#if !v.images.length}<p class="text-sm text-muted-foreground">Aucune image dans Douze points : pastille « 12 points » et bandeau bleu nuit.</p>{/if}
            <ul class="grid gap-2 sm:grid-cols-2" aria-label="Images de l'évènement">
              {#each v.images as im (im.sorte)}
                <li class="flex min-w-0 items-center gap-2 rounded-lg border p-2">
                  {#if im.presente}<img src={`/api/eurovisions/${id}/image/${im.sorte}`} alt={NOMS[im.sorte]} class="size-14 shrink-0 rounded object-cover {images[im.sorte] ? '' : 'opacity-30'}" />
                  {:else}<span class="grid size-14 shrink-0 place-items-center rounded bg-muted text-[0.6rem] text-muted-foreground">illisible</span>{/if}
                  <span class="grid min-w-0 flex-1 text-sm"><b>{NOMS[im.sorte]}</b><span class="text-xs text-muted-foreground">{ROLES[im.sorte]}{v.image_une === im.sorte ? ' · en une' : ''}</span></span>
                  <label class="flex shrink-0 items-center gap-1 text-xs"><input type="checkbox" bind:checked={images[im.sorte]} onchange={toucher} />Garder</label>
                </li>
              {/each}
            </ul>
          </Element>
        </section>

        <section class="min-w-0 rounded-2xl border bg-card p-4 {cadre(2)}" aria-label="Page 2">
          {@render alerte(2)}
          {#if v.livret === 'qualifies'}
            <h2 class="etiquette mb-2">Page 2 · nos 10 contre les 10 de l'Europe</h2>
            <Element cle="qualifies" page={2} titre="Qualifiés (calculés par Douze points)" valeur={v.demi}>
              <div class="grid gap-3 sm:grid-cols-2">
                {@render liste('Notre top 10', v.demi.notre_top.map((x) => `${x.pays} ${x.qualifie ? '✓' : '✗'}`))}
                {@render liste('Les qualifiés (ordre alphabétique)', v.demi.qualifies)}
              </div>
            </Element>
          {:else}
            <h2 class="etiquette mb-2">Page 2 · les podiums</h2>
            <Element cle="podiums" page={2} titre="Podiums (calculés par Douze points)" valeur={[v.podium_maison, v.podium_officiel]}>
              <div class="grid gap-3 sm:grid-cols-2">
                {@render liste('Chez nous', v.podium_maison)}
                {@render liste('Le vrai résultat', v.podium_officiel)}
              </div>
            </Element>
          {/if}
        </section>

        <section class="min-w-0 rounded-2xl border bg-card p-4 {cadre(3)}" aria-label="Page 3">
          {@render alerte(3)}
          <h2 class="etiquette mb-2">Page 3</h2>
          <Element cle="faits" page={3} titre={v.livret === 'qualifies' ? 'Pleurés, détestés, flair, coup de cœur' : 'Bien vu, raté, haut du palmarès'}
                   valeur={[v.mieux, v.rates, v.palmares, v.demi ?? null]}>
            <div class="grid gap-3 sm:grid-cols-2">
              {#if v.livret === 'qualifies'}
                {@render liste('On les pleure', v.demi.pleure)}
                {@render liste('On les déteste', v.demi.deteste)}
                {@render liste('Le flair des invités (haut seulement)', v.palmares.map((x) => `${x.prenom} : ${x.trouves} sur ${x.sur}`))}
                <p class="text-sm">Coup de cœur : {v.demi.coup_de_coeur || '—'} · Nul point : {v.demi.nul_point || '—'}</p>
              {:else}
                {@render liste('Bien vu', v.mieux)}
                {@render liste('Raté', v.rates)}
                {@render liste('Haut du palmarès (invité en une retiré)', v.palmares.map((x) => `${x.prenom} (${x.rang}e)`))}
              {/if}
            </div>
          </Element>
          <div class="mt-3 mb-1 flex flex-wrap items-center justify-between gap-2">
            <h3 class="etiquette">Entendu dans le salon ({commentaires.length})</h3>
            <Button size="sm" variant="outline" onclick={() => tirer({})} disabled={!v.commentaires_dispo}><Shuffle class="size-3.5" aria-hidden="true" />Nouveau tirage</Button>
          </div>
          <p class="mb-2 text-xs text-muted-foreground">2 ou 3 commentaires tirés au hasard parmi les {v.commentaires_dispo} de la soirée (aucune IA). Tous restent dans la fiche PDF de Douze points.</p>
          <ul class="grid gap-1.5">
            {#each commentaires as c (c.cle)}
              <li class="min-w-0">
                <Element cle="comm:{c.cle}" page={3} titre="{c.prenom} · {c.pays}" valeur={c.texte} changer="Un autre, tiré au hasard"
                         onchanger={() => tirer({ remplacer: c.cle })} onrefuser={() => tirer({ refuser: c.cle })}>
                  <p class="font-serif text-sm italic">« {c.texte} »</p>
                </Element>
              </li>
            {:else}<li class="text-sm text-muted-foreground">Aucun commentaire imprimé.</li>{/each}
          </ul>
        </section>

        <section class="min-w-0 rounded-2xl border bg-card p-4 {cadre(4)}" aria-label="Page 4">
          {@render alerte(4)}
          <h2 class="etiquette mb-2">Page 4 · les jumeaux de vote ({duos.length})</h2>
          {#if !v.immich}<p class="mb-2 text-xs text-muted-foreground">Immich n'est pas réglé (GAZETTE_IMMICH_CLE) : les duos sont imprimés sur fond du logo.</p>{/if}
          <ul class="grid gap-3 sm:grid-cols-2">
            {#each duos as x (x.cle)}
              <li class="min-w-0">
                <Element cle="duo:{x.cle}" page={4} titre={x.noms} valeur={{ p: x.photo, r: x.retiree }}
                         onchanger={x.photos.length > 1 ? () => autrePhoto(x) : null} changer="Une autre photo du duo"
                         onrefuser={x.photo && !x.retiree ? () => { x.retiree = true; toucher() } : null}>
                  <div class="relative aspect-[4/3] overflow-hidden rounded-lg bg-muted">
                    {#if x.photo && !x.retiree}
                      <img src={`/api/eurovisions/${id}/photo/${x.photo}`} alt="Photo du duo {x.noms}" loading="lazy" class="size-full object-cover" />
                    {:else}
                      <span class="grid size-full place-items-center text-sm text-muted-foreground">{x.photos.length ? 'photo retirée : fond du logo' : 'pas de photo : fond du logo'}</span>
                    {/if}
                  </div>
                  {#if x.retiree && x.photos.length}<button type="button" class="text-xs text-muted-foreground underline hover:text-foreground" onclick={() => { x.retiree = false; x.photo = x.photo || x.photos[0]; toucher() }}>Remettre la photo</button>{/if}
                </Element>
              </li>
            {:else}<li class="text-sm text-muted-foreground">Pas de jumeaux de vote ce soir.</li>{/each}
          </ul>
          {#if v.livret === 'qualifies'}
            <Element cle="rdv" page={4} titre="Rendez-vous samedi" valeur={[v.demi.favoris, v.demi.date_finale]}>
              <p class="text-sm">Nos favoris : {v.demi.favoris.join(', ') || '—'}{v.demi.date_finale ? ` · finale le ${dateLongue(v.demi.date_finale)}` : ''}</p>
            </Element>
          {/if}
        </section>

        <section class="min-w-0 rounded-2xl border bg-card p-4 text-sm" aria-label="Carnet">
          <h2 class="etiquette mb-2">À l'approbation</h2>
          <p class="text-muted-foreground">La parution est notée sur la fiche carnet (« Journaux parus ») de chaque invité lié :</p>
          <ul class="mt-1 flex flex-wrap gap-2">{#each d.carnet as i}<li class="rounded-full border px-2 py-0.5 text-xs {i.carnet ? 'border-valide/60' : 'text-muted-foreground'}">{i.prenom}{i.carnet ? '' : ' · pas dans carnet'}</li>{/each}</ul>
          {#if n.carnet}<p class="mt-2 text-xs text-muted-foreground">Dernier envoi : {n.carnet}.</p>{/if}
        </section>
      </div>
    </div>

    <aside class="lg:sticky lg:top-6 lg:self-start" aria-label="Aperçu">
      <div class="mb-2 flex flex-wrap items-center justify-between gap-2">
        <h2 class="etiquette">Aperçu{modifie ? ' (enregistre pour mettre à jour)' : ''}</h2>
        <span class="flex gap-3 text-xs">
          <a class="inline-flex items-center gap-1 text-muted-foreground hover:text-foreground" href={`/api/eurovisions/${id}/pdf?mode=impose`}><Download class="size-3.5" aria-hidden="true" />PDF à imprimer</a>
          <a class="inline-flex items-center gap-1 text-muted-foreground hover:text-foreground" href={`/api/eurovisions/${id}/pdf?mode=lecture`}><Download class="size-3.5" aria-hidden="true" />PDF lecture</a>
        </span>
      </div>
      <div class="max-h-[78vh] overflow-y-auto rounded-xl border" bind:clientWidth={largeur}>
        <div style="height:{Math.round(3480 * echelle)}px;position:relative;overflow:hidden">
          <iframe title="Aperçu de l'édition spéciale" src={`/api/eurovisions/${id}/apercu?mode=ecran&t=${tampon}`} scrolling="no"
                  style="position:absolute;top:0;left:0;width:600px;height:3480px;border:0;transform:scale({echelle});transform-origin:0 0"></iframe>
        </div>
      </div>
      <p class="mt-2 text-xs text-muted-foreground">Impression : A4 paysage, recto-verso bord court, puis plier en deux. Le PDF lecture sert aux absents.</p>
    </aside>
  </div>
{:else if message}
  <p class="text-sm text-destructive" role="alert">{message}</p>
{:else}
  <p class="text-sm text-muted-foreground">Lecture…</p>
{/if}
