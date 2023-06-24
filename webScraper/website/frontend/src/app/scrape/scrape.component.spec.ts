import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ScrapeComponent } from './scrape.component';

describe('ScrapeComponent', () => {
  let component: ScrapeComponent;
  let fixture: ComponentFixture<ScrapeComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      declarations: [ScrapeComponent]
    });
    fixture = TestBed.createComponent(ScrapeComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
