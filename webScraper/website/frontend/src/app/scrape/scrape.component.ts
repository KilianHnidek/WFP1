import { Component } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { FormGroup, FormControl } from '@angular/forms';

@Component({
  selector: 'app-scrape',
  templateUrl: './scrape.component.html',
  styleUrls: ['./scrape.component.scss']
})
export class ScrapeComponent {
  form: FormGroup = new FormGroup({
    city: new FormControl(''),
    date: new FormControl(''),
    nights: new FormControl(''),
    guests: new FormControl(''),
    rooms: new FormControl(''),
    accommodation: new FormControl('')
  });
  apiUrl = '/scraper/scrape';

  constructor(private http: HttpClient) {}


  onSubmit() {
    console.log(this.form.value);
    this.http.post(this.apiUrl, this.form.value).subscribe(res => {
      console.log(res);
    }, err => {
      console.log(err);
    });
  }
}
