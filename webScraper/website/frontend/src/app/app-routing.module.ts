import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';

import { AboutComponent } from './about/about.component';
import { IndexComponent } from './index/index.component';
import { AnalysisComponent } from './analysis/analysis.component';
import { ScrapeComponent } from './scrape/scrape.component';

const routes: Routes = [
  { path: '', component: IndexComponent },
  { path: 'about', component: AboutComponent },
  { path: 'analysis', component: AnalysisComponent },
  { path: 'scrape', component: ScrapeComponent },
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule { }
