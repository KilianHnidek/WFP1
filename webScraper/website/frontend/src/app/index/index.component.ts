import { Component, OnInit } from '@angular/core';
import { HttpClient } from '@angular/common/http';

@Component({
  selector: 'app-index',
  templateUrl: './index.component.html',
  styleUrls: ['./index.component.scss']
})
export class IndexComponent {
  apiUrl = '/backend';

  constructor(private http: HttpClient) { }


  testfuntion(): void {
    this.http.get<any>(this.apiUrl).subscribe(response => {
      console.log(response);
    });
  }
}
